"""Optional publication-style plots; execute with the recorded plotting environment."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .campaign import OUT,load,dump,sha,timestamp

def main():
    data=load(OUT/"PAIRED_PARAMETER_UNIT_CI.json")
    conditions=load(OUT/"PREREGISTERED_SPEC.json")["conditions"]
    metrics=[("stepwise_excess_vs_clean_u","Excess emitted vs clean (research U)"),("stepwise_deficit_vs_clean_u","Deficit vs clean (research U)"),("longest_interruption_min","Longest interruption (min)"),("time_below70_pct","Time below70mg/dL (percentage points)")]
    folder=OUT/"figures";folder.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size":9,"svg.fonttype":"none","axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(2,2,figsize=(13,10),constrained_layout=True)
    for ax,(metric,label) in zip(axes.flat,metrics):
        for family,offset,color in (("geco_original",-.14,"#24658C"),("hovorka_2004",.14,"#B56835")):
            records=[r for r in data if r["mode"]=="main" and r["family"]==family and r["arm_a"]=="full_supervised" and r["arm_b"]=="simple_supervised" and r["metric"]==metric]
            by={r["condition"]:r for r in records}
            for i,c in enumerate(conditions):
                r=by.get(c)
                if r:
                    mean=r["mean_paired_difference"]
                    ax.errorbar(mean,i+offset,xerr=[[max(0,mean-r["ci95_low"])] ,[max(0,r["ci95_high"]-mean)]],fmt="o",color=color,capsize=2,label=family if i==0 else None)
        ax.axvline(0,color=".5",linestyle=":",linewidth=1)
        ax.set_yticks(range(len(conditions)),conditions);ax.invert_yaxis();ax.set_xlabel(label);ax.grid(axis="x",alpha=.2)
    axes[0,0].legend(loc="best")
    fig.suptitle("Full minus simple detector, supervised-reset emulation\nFixed clean-command intervention; paired95% intervals resample synthetic parameter units",fontsize=12)
    outputs=[]
    for suffix in ("svg","png","pdf"):
        p=folder/("F01_paired_detector_effects."+suffix);fig.savefig(p,dpi=180);outputs.append({"path":str(p.relative_to(OUT)),"sha256":sha(p)})
    plt.close(fig)
    dump(folder/"FIGURE_MANIFEST.json",{"generated_utc":timestamp(),"matplotlib_version":matplotlib.__version__,"source_results_sha256":sha(OUT/"PAIRED_PARAMETER_UNIT_CI.json"),"script_sha256":sha(__file__),"outputs":outputs,"scope":"Scientific effect plot; glucose outcomes require separate invalid-physiology counts, not a clinical chart; no visual review claimed by generation alone"})

if __name__=="__main__":main()
