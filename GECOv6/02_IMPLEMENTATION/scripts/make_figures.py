"""Publication figures for GECO v4 from the campaign CSVs. Writes to results/figures/."""
import os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "results", "campaign")
F = os.path.join(ROOT, "results", "figures"); os.makedirs(F, exist_ok=True)
plt.rcParams.update({"font.size": 11, "figure.dpi": 150, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})
TEAL, AMBER, RED, GREEN, BLUE, GREY = "#0FA89B", "#E8A02A", "#D3343F", "#2FB85A", "#2C8CD6", "#7A7F8A"

rep = pd.read_csv(os.path.join(C, "replay_attack_matrix.csv"))
agg = pd.read_csv(os.path.join(C, "replay_attack_matrix_aggregate.csv"))
ben = pd.read_csv(os.path.join(C, "benign_replay.csv"))
clo = pd.read_csv(os.path.join(C, "closed_loop_ablation.csv"))

NAMES = {"RF-01":"Passive eavesdrop","RF-02":"CGM replay","RF-03":"CGM spoof","RF-04":"Cmd injection",
 "RF-05":"MITM CGM bias","RF-05b":"MITM CGM +80","RF-05r":"MITM CGM ramp","RF-05f":"MITM CGM freeze",
 "RF-06":"MITM cmd x5","RF-07":"Delay/loss/reorder","RF-08":"Rogue pairing","RF-09":"Jamming",
 "RF-10":"Credentialed ctrl","ACT-01":"Firmware over-deliver","ACT-02":"Under/occlusion",
 "ACT-03":"Stuck-on motor","ACT-04":"False ack","INT-01":"Rogue config","INT-02":"Log tamper",
 "COORD-01":"CGM+cmd combo","COORD-02":"Replay+credentialed","COORD-03":"Coherent digital","COORD-04":"+forged truth (undetectable)"}

# ---------------- FIG 1: layered-defence attack matrix (protected profile) ----------------
def fig_matrix():
    order = ["RF-01","RF-02","RF-03","RF-04","RF-05","RF-05b","RF-05r","RF-05f","RF-06","RF-07","RF-08","RF-09",
             "RF-10","ACT-01","ACT-02","ACT-03","ACT-04","INT-01","INT-02","COORD-01","COORD-02","COORD-03","COORD-04"]
    prof = agg[agg.profile=="protected"].set_index("attack_id")
    rows=[]
    for aid in order:
        r=prof.loc[aid]
        prev = r["prevention_rate_mean"]
        det = max(r["contain_detect_frac"], r["physiology_alarm_frac"])
        mit = r["cutoff_frac"]
        rows.append([0 if np.isnan(prev) else prev, det, mit])
    M=np.array(rows)
    fig,ax=plt.subplots(figsize=(7.2, 9.2))
    cmap=LinearSegmentedColormap.from_list("g",["#f4f6f8","#bfe9df","#0FA89B"])
    im=ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks([0,1,2]); ax.set_xticklabels(["Prevention\n(crypto/protocol)","Detection\n(twins/evidence)","Mitigation\n(cut-off)"])
    ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{a}  {NAMES[a]}" for a in order], fontsize=9)
    for i in range(len(order)):
        for j in range(3):
            ax.text(j,i,f"{M[i,j]:.2f}",ha="center",va="center",fontsize=8,color="#12333a" if M[i,j]<0.6 else "white")
    ax.set_title("GECO v4 layered defence — protected profile\nfraction of participants each layer acts (n=27)", fontsize=12)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="fraction acting")
    # mark the undetectable set
    ax.add_patch(plt.Rectangle((-0.5, len(order)-1-0.5), 3, 1, fill=False, edgecolor=RED, lw=2.5))
    fig.tight_layout(); fig.savefig(os.path.join(F,"fig1_attack_matrix.png")); plt.close(fig)

# ---------------- FIG 2: ablation — excess insulin the attacker forces through ----------------
def fig_ablation():
    atks=["RF-06","RF-10","ACT-01","ACT-03","COORD-01","COORD-03","COORD-04"]
    piv=clo[clo.profile=="legacy"].pivot_table(index="attack_id",columns="ablation",values="excess_u_during_attack",aggfunc="median")
    cols=["no_geco","kernel_only","geco_no_delivery","geco_full"]
    labels=["No GECO","Kernel only","GECO w/o\ndelivery twin","GECO full"]
    colours=[GREY,"#9aa0ab",AMBER,TEAL]
    x=np.arange(len(atks)); w=0.2
    fig,ax=plt.subplots(figsize=(11,5.4))
    for k,(c,lab,col) in enumerate(zip(cols,labels,colours)):
        vals=[piv.loc[a,c] for a in atks]
        ax.bar(x+(k-1.5)*w, vals, w, label=lab, color=col)
    ax.axhline(0,color="#333",lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([NAMES[a] for a in atks], rotation=18, ha="right", fontsize=9)
    ax.set_ylabel("Median excess insulin forced through during attack (U)")
    ax.set_title("Ablation: only the full three-twin GECO (with delivery reconciliation + cut-off) removes the excess\nNegative = GECO delivered less than the attacker demanded.  COORD-04 = declared undetectable set")
    ax.legend(frameon=False, ncol=4, loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(F,"fig2_ablation_excess.png")); plt.close(fig)

# ---------------- FIG 3: benign false-alarm burden ----------------
def fig_benign():
    g=ben.groupby("participant").agg(fc=("false_containment_episodes_per_benign_day","mean"),
                                     ph=("phys_alarms_per_day","mean"),
                                     trip=("cutoff_tripped","max")).reset_index().sort_values("fc")
    fig,axs=plt.subplots(1,2,figsize=(12,4.6))
    axs[0].bar(range(len(g)), g.fc, color=[RED if t else TEAL for t in g.trip])
    axs[0].set_title(f"False containment per benign patient-day (median {ben.false_containment_episodes_per_benign_day.median():.2f})")
    axs[0].set_xlabel("participant (sorted)"); axs[0].set_ylabel("episodes / benign day")
    axs[0].axhline(1.0, color=GREY, ls="--", lw=1, label="1/day budget"); axs[0].legend(frameon=False)
    axs[1].hist(g.ph, bins=12, color=BLUE, alpha=0.85)
    axs[1].set_title(f"Physiology alarms/day on benign locked test (median {ben.phys_alarms_per_day.median():.2f})")
    axs[1].set_xlabel("alarms / day"); axs[1].set_ylabel("participants")
    fig.suptitle("Benign burden on real T1D data (HUPA-UCM + D1NAMO locked test windows, n=27)", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(F,"fig3_benign_burden.png")); plt.close(fig)

# ---------------- FIG 4: exemplar traces (legacy no_geco vs geco_full) ----------------
def fig_traces():
    pairs=[("RF-10","Credentialed malicious controller"),("ACT-01","Firmware over-delivery (2x)"),("COORD-04","Coherent + forged truth (undetectable)")]
    fig,axs=plt.subplots(len(pairs),1,figsize=(11,9.5),sharex=True)
    for ax,(aid,title) in zip(axs,pairs):
        try:
            ng=pd.read_csv(os.path.join(C,"traces_closed",f"HUPA0001P_{aid}_legacy_no_geco.csv"))
            gf=pd.read_csv(os.path.join(C,"traces_closed",f"HUPA0001P_{aid}_legacy_geco_full.csv"))
        except FileNotFoundError:
            continue
        ax.plot(ng.t_min/60, ng.true_glucose, color=RED, lw=1.8, label="no GECO")
        ax.plot(gf.t_min/60, gf.true_glucose, color=TEAL, lw=1.8, label="GECO full")
        aw=ng[ng.attack_active==True]
        if len(aw): ax.axvspan(aw.t_min.min()/60, aw.t_min.max()/60, color=AMBER, alpha=0.15, label="attack")
        cut=gf[gf.cutoff==True]
        if len(cut): ax.axvline(cut.t_min.min()/60, color=GREEN, ls="--", lw=1.4, label="cut-off")
        ax.axhspan(70,180,color=GREEN,alpha=0.06); ax.axhline(70,color=GREY,ls=":",lw=1)
        ax.set_ylabel("glucose mg/dL"); ax.set_title(f"{aid} — {title}", fontsize=10, loc="left")
        ax.set_ylim(40,320)
    axs[0].legend(frameon=False, ncol=4, fontsize=9)
    axs[-1].set_xlabel("hours")
    fig.suptitle("Closed-loop virtual patient (HUPA0001P): what reaches the body with and without GECO", fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(F,"fig4_exemplar_traces.png")); plt.close(fig)

# ---------------- FIG 5: prevention vs detection (legacy vs protected) ----------------
def fig_prev_vs_det():
    net=["RF-02","RF-03","RF-04","RF-05","RF-06","RF-07"]
    L=agg[agg.profile=="legacy"].set_index("attack_id"); P=agg[agg.profile=="protected"].set_index("attack_id")
    x=np.arange(len(net)); w=0.35
    fig,ax=plt.subplots(figsize=(9.5,4.8))
    ax.bar(x-w/2,[0 if np.isnan(L.loc[a,'prevention_rate_mean']) else L.loc[a,'prevention_rate_mean'] for a in net],w,label="Legacy profile",color=AMBER)
    ax.bar(x+w/2,[0 if np.isnan(P.loc[a,'prevention_rate_mean']) else P.loc[a,'prevention_rate_mean'] for a in net],w,label="Protected profile",color=TEAL)
    ax.set_xticks(x); ax.set_xticklabels([NAMES[a] for a in net], rotation=15, ha="right", fontsize=9)
    ax.set_ylabel("Fraction of malicious messages prevented"); ax.set_ylim(0,1.05)
    ax.set_title("What cryptography actually prevents: legacy vs protected link profile\n(the same bench, same attacker) — network attacks that legacy accepts are rejected at the gateway")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(F,"fig5_prevention.png")); plt.close(fig)

for fn in (fig_matrix, fig_ablation, fig_benign, fig_traces, fig_prev_vs_det):
    fn(); print("wrote", fn.__name__, flush=True)
print("FIGURES DONE ->", F)
