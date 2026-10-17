"""Independent offline plant adapters; see PLANT_EQUATIONS_AND_PROVENANCE.md.

Hovorka equations1–7, doi:10.1088/0967-3334/25/4/010. No controller,
patient dataset, security pathway or hardware connection exists here.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
from geco_v4.physiology import GlucoseModel, TwinParams

MMOL_TO_MGDL = 18.01559
GRAMS_GLUCOSE_PER_MMOL = .1801559

@dataclass(frozen=True)
class HovorkaParams:
    weight_kg: float = 75.0
    k12: float = .066
    ka1: float = .006
    ka2: float = .06
    ka3: float = .03
    ke: float = .138
    vi_l_per_kg: float = .12
    vg_l_per_kg: float = .16
    ag: float = .8
    tmax_g_min: float = 40.0
    tmax_i_min: float = 55.0
    sit: float = 51.2e-4
    sid: float = 8.2e-4
    sie: float = 520e-4
    egp_mmol_kg_min: float = .0161
    f01_mmol_kg_min: float = .0097
    sensor_lag_min: float = 9.0  # study observation extension, not Hovorka equation
    dt_min: float = 5.0
    integration_step_min: float = 1.0

    def __post_init__(self):
        for key, value in asdict(self).items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        if not 0 < self.ag <= 1:
            raise ValueError("ag must be at most1")

class HovorkaPlant:
    """Q1,Q2 [mmol], S1,S2 [mU], I [mU/L], x1,x2 [1/min],
    x3 [unitless], D1,D2 [mmol], interstitial sensor extension [mg/dL].
    Oral input and subcutaneous insulin are uniform rates over each5-min bin.
    No clamp is applied to the published EGP term or glucose compartments;
    out-of-domain trajectories remain visible to validity accounting.
    """
    def __init__(self, params=None):
        self.p = params or HovorkaParams()
        self.basal_u = 0.0
        self.x = self.initial_state(120.0)

    def initial_state(self, mgdl=120.0):
        p=self.p; vg=p.vg_l_per_kg*p.weight_kg; vi=p.vi_l_per_kg*p.weight_kg
        q1=mgdl/MMOL_TO_MGDL*vg
        def balance(ins):
            x1,x2,x3=p.sit*ins,p.sid*ins,p.sie*ins
            f01=p.f01_mmol_kg_min*p.weight_kg*min(1.,max(0.,mgdl/MMOL_TO_MGDL)/4.5)
            fr=.003*max(0.,mgdl/MMOL_TO_MGDL-9)*vg
            return -f01-fr-x1*q1*x2/(p.k12+x2)+p.egp_mmol_kg_min*p.weight_kg*(1-x3)
        lo,hi=0.,1/p.sie
        if balance(lo)<0 or balance(hi)>0:
            raise ValueError("No nonnegative fasting equilibrium for synthetic parameters")
        for _ in range(80):
            mid=(lo+hi)/2
            if balance(mid)>0: lo=mid
            else: hi=mid
        ins=(lo+hi)/2; rate=ins*p.ke*vi
        self.basal_u=rate*p.dt_min/1000
        x1,x2,x3=p.sit*ins,p.sid*ins,p.sie*ins
        return np.array([q1,x1*q1/(p.k12+x2),rate*p.tmax_i_min,rate*p.tmax_i_min,ins,x1,x2,x3,0.,0.,mgdl])

    def derivative(self,x,insulin_u_min,carbs_g_min):
        p=self.p
        q1,q2,s1,s2,ins,x1,x2,x3,d1,d2,gi=x
        vg=p.vg_l_per_kg*p.weight_kg; vi=p.vi_l_per_kg*p.weight_kg
        g=q1/vg
        # fc01 ->0 at zero glucose; retain negative out-of-domain g in states.
        fc01=p.f01_mmol_kg_min*p.weight_kg*min(1.,max(0.,g)/4.5)
        fr=.003*max(0.,g-9)*vg
        return np.array([
            -fc01-x1*q1+p.k12*q2-fr+d2/p.tmax_g_min+p.egp_mmol_kg_min*p.weight_kg*(1-x3),
            x1*q1-(p.k12+x2)*q2,
            insulin_u_min*1000-s1/p.tmax_i_min,
            (s1-s2)/p.tmax_i_min,
            s2/(p.tmax_i_min*vi)-p.ke*ins,
            p.ka1*(p.sit*ins-x1), p.ka2*(p.sid*ins-x2), p.ka3*(p.sie*ins-x3),
            carbs_g_min*p.ag/GRAMS_GLUCOSE_PER_MMOL-d1/p.tmax_g_min,
            (d1-d2)/p.tmax_g_min,
            (g*MMOL_TO_MGDL-gi)/p.sensor_lag_min,
        ])

    def step(self, insulin_u, carbs_g):
        if not all(math.isfinite(v) and v>=0 for v in (insulin_u,carbs_g)):
            raise ValueError("finite nonnegative per-bin inputs required")
        p=self.p;n=math.ceil(p.dt_min/p.integration_step_min);h=p.dt_min/n
        u=insulin_u/p.dt_min;c=carbs_g/p.dt_min;x=self.x
        for _ in range(n):
            a=self.derivative(x,u,c);b=self.derivative(x+.5*h*a,u,c)
            d=self.derivative(x+.5*h*b,u,c);e=self.derivative(x+h*d,u,c)
            x=x+h/6*(a+2*b+2*d+e)
        self.x=x
        return self.glucose, self.sensor

    @property
    def glucose(self): return float(self.x[0]/(self.p.vg_l_per_kg*self.p.weight_kg)*MMOL_TO_MGDL)
    @property
    def sensor(self): return float(self.x[-1])
    @property
    def valid(self): return bool(np.isfinite(self.x).all() and np.all(self.x[:10]>=0) and self.x[7]<=1 and 0<self.glucose<1000)
    @property
    def diagnostics(self):
        return {"negative_egp_evaluator_only":bool(self.x[7]>1),"endogenous_production_mmol_min":float(self.p.egp_mmol_kg_min*self.p.weight_kg*(1-self.x[7])),"plasma_glucose_clamped":False,"interstitial_glucose_clamped":False,"remote_action_clamped":False}

class OriginalPlant:
    def __init__(self, params):
        self.p=params;self.model=GlucoseModel(params)
        self.basal_u=params.ib*params.ki*params.dt_min/params.ku
        self.x=self.model.initial_state(params.gb,self.basal_u)
    def step(self,insulin_u,carbs_g):
        self.x=self.model.step(self.x,insulin_u,carbs_g)
        return self.glucose,self.sensor
    @property
    def glucose(self): return float(self.x[0])
    @property
    def sensor(self): return float(self.x[4])
    @property
    def valid(self): return bool(np.isfinite(self.x).all() and 20<self.glucose<600)
    @property
    def diagnostics(self):
        return {"negative_egp_evaluator_only":False,"endogenous_production_mmol_min":None,"plasma_glucose_clamped":bool(self.x[0]<=20 or self.x[0]>=600),"interstitial_glucose_clamped":bool(self.x[4]<=20 or self.x[4]>=600),"remote_action_clamped":bool(self.x[1]<=-.5*self.p.p1+1e-14)}

def make_plant(unit):
    f=unit["factors"]
    if unit["family"]=="hovorka_2004":
        p=HovorkaParams(weight_kg=unit["body_weight_kg"],sit=51.2e-4*f["sensitivity"],sid=8.2e-4*f["sensitivity"],sie=520e-4*f["sensitivity"],tmax_g_min=40*f["absorption"],tmax_i_min=55*f["absorption"],ke=.138*f["clearance"],egp_mmol_kg_min=.0161*f["glucose_flux"],f01_mmol_kg_min=.0097*f["glucose_effectiveness"],ag=min(.99,.8*f["gut_gain"]))
        return HovorkaPlant(p)
    p=TwinParams(gb=120.,p1=.006*f["glucose_effectiveness"],egp=.006*f["glucose_effectiveness"]*120,p3=6e-5*f["sensitivity"],ki=.03*f["clearance"],ka=.025/f["absorption"],kc=.4*f["gut_gain"])
    return OriginalPlant(p)
