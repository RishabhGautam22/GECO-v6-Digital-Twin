"""Architecture / concept diagrams for GECO v4 (matplotlib, theme-consistent). -> results/figures/"""
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, "results", "figures"); os.makedirs(F, exist_ok=True)
TEAL,AMBER,RED,GREEN,BLUE,GREY,PUR,INK="#0FA89B","#E8A02A","#D3343F","#2FB85A","#2C8CD6","#7A7F8A","#8155C6","#12333a"
plt.rcParams.update({"font.family":"DejaVu Sans"})

def box(ax,x,y,w,h,txt,fc,tc="white",fs=11,ec=None,r=0.03,bold=True):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.01,rounding_size={r}",fc=fc,ec=ec or fc,lw=1.6))
    ax.text(x+w/2,y+h/2,txt,ha="center",va="center",color=tc,fontsize=fs,fontweight="bold" if bold else "normal",wrap=True)

def arrow(ax,p0,p1,c=INK,style="-|>",lw=2,ls="-"):
    ax.add_patch(FancyArrowPatch(p0,p1,arrowstyle=style,mutation_scale=16,color=c,lw=lw,ls=ls,shrinkA=2,shrinkB=2))

# ---------- DIAGRAM 1: three-twin architecture ----------
def arch():
    fig,ax=plt.subplots(figsize=(13,7.4)); ax.set_xlim(0,13); ax.set_ylim(0,7.4); ax.axis("off")
    ax.text(6.5,7.1,"GECO v4 — composite three-twin runtime-assurance architecture",ha="center",fontsize=15,fontweight="bold",color=INK)
    # inputs
    box(ax,0.3,5.6,2.2,0.9,"CGM endpoint\n(sensor stream)",BLUE,fs=10)
    box(ax,0.3,4.3,2.2,0.9,"Controller / phone\n(therapy command)",AMBER,fs=10)
    box(ax,0.3,3.0,2.2,0.9,"Pump endpoint\n(acknowledgement)",AMBER,fs=10)
    box(ax,0.3,1.5,2.2,1.0,"Independent balance\n(delivered saline mass)",GREEN,fs=10)
    # twins
    box(ax,3.3,5.3,3.3,1.3,"PHYSIOLOGY TWIN\nEKF standardised innovation\n+ 30-min forecast + CUSUM",PUR,fs=9)
    box(ax,3.3,3.6,3.3,1.3,"PROTOCOL-STATE TWIN\nidentity, HMAC, nonce,\nsequence, freshness, ack",BLUE,fs=9)
    box(ax,3.3,1.7,3.3,1.3,"DELIVERY-RECONCILIATION\nTWIN — commanded U vs\nmeasured mass (ground truth)",GREEN,fs=9)
    # fusion
    box(ax,7.0,3.3,2.7,2.0,"DEPENDENCY-\nAWARE FUSION\nno double-count\nwithin a group;\nabstain if a group\nis missing",TEAL,fs=9)
    # kernel + cutoff
    box(ax,10.0,4.4,2.7,1.5,"DETERMINISTIC\nSAFETY KERNEL\nbounded authority ·\npredictive-low & stale stop",INK,fs=10)
    box(ax,10.0,2.4,2.7,1.4,"INDEPENDENT\nde-energize-to-safe\nPHYSICAL CUT-OFF",RED,fs=10)
    box(ax,10.0,0.8,2.7,1.1,"Human + audit\nreason codes · hash chain",GREY,fs=10)
    for y in (6.0,4.75,3.45):
        arrow(ax,(2.5,y),(3.4,5.9 if y>5 else (4.2 if y>4 else 2.3)))
    arrow(ax,(2.5,6.0),(3.4,5.95),PUR); arrow(ax,(2.5,4.75),(3.4,4.2),BLUE); arrow(ax,(2.5,3.45),(3.4,4.0),BLUE)
    arrow(ax,(2.5,2.0),(3.4,2.3),GREEN)
    for y in (5.95,4.25,2.35): arrow(ax,(6.6,y),(7.0,4.3),TEAL,lw=1.6)
    arrow(ax,(9.7,4.6),(10.0,5.1),INK)
    arrow(ax,(9.7,3.9),(10.0,3.1),RED,ls="--")
    arrow(ax,(11.35,4.4),(11.35,3.8),RED)
    arrow(ax,(11.35,2.4),(11.35,1.9),GREY)
    ax.text(6.5,0.3,"Prevention (crypto/protocol)  ·  Detection (three twins)  ·  Mitigation (kernel + physical cut-off)  —  measured separately",
            ha="center",fontsize=10.5,color=INK,style="italic")
    fig.savefig(os.path.join(F,"diag_architecture.png"),dpi=150,bbox_inches="tight"); plt.close(fig)

# ---------- DIAGRAM 2: trust domains + attacker ----------
def trust():
    fig,ax=plt.subplots(figsize=(12,6.4)); ax.set_xlim(0,12); ax.set_ylim(0,6.4); ax.axis("off")
    ax.text(6,6.05,"Trust domains and the man-in-the-middle — what each attacker can and cannot forge",ha="center",fontsize=14,fontweight="bold",color=INK)
    box(ax,0.4,3.6,2.0,1.2,"cgm-01\nCGM key",BLUE,fs=10)
    box(ax,0.4,1.4,2.0,1.2,"HOST\nreplay + orchestrator",GREY,fs=10)
    box(ax,4.6,4.4,2.6,1.3,"gw-01  GECO\ngateway key",TEAL,fs=10)
    box(ax,8.4,4.4,2.4,1.3,"pump-01\npump key",AMBER,fs=10)
    box(ax,8.4,1.4,2.4,1.3,"truth-01\nbalance + cut-off\n(independent)",GREEN,fs=10)
    box(ax,4.4,1.2,3.0,1.4,"ATTACKER (MITM)\ndrop · delay · modify · inject\n· holds only granted keys",RED,fs=10)
    arrow(ax,(2.4,4.2),(4.6,5.0),BLUE); arrow(ax,(7.2,5.0),(8.4,5.0),AMBER)
    arrow(ax,(9.6,4.4),(9.6,2.7),GREEN,ls="--"); ax.text(9.75,3.5,"saline\nmass",color=GREEN,fontsize=9)
    arrow(ax,(5.9,2.6),(5.9,4.4),RED,ls=":"); arrow(ax,(5.9,2.6),(8.4,4.6),RED,ls=":")
    ax.text(6.0,0.6,"COORD-04 = attacker forges every witness INCLUDING truth-01 → declared undetectable set (GECO abstains)",
            ha="center",fontsize=10.5,color=RED,fontweight="bold")
    fig.savefig(os.path.join(F,"diag_trust_domains.png"),dpi=150,bbox_inches="tight"); plt.close(fig)

# ---------- DIAGRAM 3: response ladder ----------
def ladder():
    fig,ax=plt.subplots(figsize=(11,5.6)); ax.set_xlim(0,11); ax.set_ylim(0,5.6); ax.axis("off")
    ax.text(5.5,5.3,"GECO v4 response ladder — therapy-preserving, deterministic, reversible",ha="center",fontsize=14,fontweight="bold",color=INK)
    steps=[("NORMAL","within validated envelope — full authority",GREEN),
           ("WATCH","raise low-burden advisory; increase diagnostic sampling; no therapy change",AMBER),
           ("CONTAIN","cap command authority (uncertain / corroborated suspicion); request confirmation",("#E8730A")),
           ("SAFE MODE","reject unsafe request; predictive-low/stale stop; deterministic conservative mode",RED),
           ("PHYSICAL CUT-OFF","independent de-energize-to-safe stops fluid if the endpoint disobeys software","#8B1E27")]
    y=4.4
    for i,(name,desc,c) in enumerate(steps):
        box(ax,0.5,y,2.4,0.7,name,c,fs=11)
        ax.text(3.1,y+0.35,desc,va="center",fontsize=10,color=INK)
        if i<len(steps)-1: arrow(ax,(1.7,y),(1.7,y-0.18),GREY,lw=1.4)
        y-=0.85
    ax.text(5.5,0.15,"Never: autonomous re-image, generative state repair, model/policy rewrite, or removing basal without a human.",
            ha="center",fontsize=9.5,color=GREY,style="italic")
    fig.savefig(os.path.join(F,"diag_response_ladder.png"),dpi=150,bbox_inches="tight"); plt.close(fig)

for fn in (arch,trust,ladder): fn(); print("wrote",fn.__name__)
print("DIAGRAMS DONE")
