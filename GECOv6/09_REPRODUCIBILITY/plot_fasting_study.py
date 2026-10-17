"""Post-outcome scientific plot of all registered supplemental conditions."""
from pathlib import Path
import json,hashlib,datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"03_EXPERIMENTS/supplement_fasting"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    data=json.loads((OUT/"PAIRED_PARAMETER_UNIT_CI.json").read_text())
    conditions=json.loads((OUT/"PREREGISTERED_SPEC.json").read_text())["conditions"]
    labels=["Clean","Emission ×2","Occlusion","Persistent flow","CGM bias +40","CGM missing","Emission ×2 + bias","Above + report masking"]
    plt.rcParams.update({"font.size":9,"svg.fonttype":"none","axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(2,2,figsize=(13,9.6),constrained_layout=True)
    for row,(arm_a,arm_b,title) in enumerate([("full_supervised","masscusum_supervised","Full minus mass-CUSUM"),("masscusum_supervised","simple_supervised","Mass-CUSUM minus simple")]):
      for col,(metric,label) in enumerate([("stepwise_excess_vs_clean_u","Excess delivery difference (research U)"),("stepwise_deficit_vs_clean_u","Delivery deficit difference (research U)")]):
        ax=axes[row,col]
        for family,offset,color in [("geco_original",-.13,"#24658C"),("hovorka_2004",.13,"#B56835")]:
            selected={r["condition"]:r for r in data if r["family"]==family and r["arm_a"]==arm_a and r["arm_b"]==arm_b and r["metric"]==metric}
            for i,condition in enumerate(conditions):
                r=selected[condition];m=r["mean_paired_difference"]
                ax.errorbar(m,i+offset,xerr=[[max(0,m-r["ci95_low"])],[max(0,r["ci95_high"]-m)]],fmt="o",markersize=4,color=color,capsize=2,label=family if i==0 else None)
        ax.axvline(0,color=".5",linestyle=":",linewidth=1)
        ax.set_yticks(range(8),labels);ax.invert_yaxis();ax.set_xlabel(label);ax.set_title(title);ax.grid(axis="x",alpha=.2)
    axes[0,0].legend(loc="upper left",fontsize=8)
    fig.suptitle("Fasting constant-request supplement: benefits and delivery costs\nExploratory 95% intervals; 16 new synthetic vectors per plant, two seeds averaged within vector",fontsize=12)
    folder=OUT/"figures";folder.mkdir(exist_ok=True);outputs=[]
    for ext in ["png","svg","pdf"]:
        p=folder/("F02_fasting_component_effects."+ext);fig.savefig(p,dpi=180);outputs.append({"path":str(p.relative_to(ROOT)),"sha256":sha(p)})
    plt.close(fig)
    receipt={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_results_sha256":sha(OUT/"PAIRED_PARAMETER_UNIT_CI.json"),"script_sha256":sha(__file__),"matplotlib":matplotlib.__version__,"outputs":outputs,"scope":"All eight registered conditions; all primary component and aggregation contrasts, excess and deficit. Negative is lower for the named delivery quantity, not overall clinical benefit. Domain screen passed in these runs; no physiological validation implied."}
    (folder/"FIGURE_MANIFEST.json").write_text(json.dumps(receipt,indent=2)+"\n")
if __name__=="__main__":main()
