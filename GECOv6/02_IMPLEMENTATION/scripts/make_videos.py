"""Explanatory MP4s for GECO v4 from closed-loop traces. Writes results/videos/*.mp4.

Each video animates a real closed-loop run: glucose, delivered vs commanded insulin,
the three evidence channels, and the safety state - with vs without GECO. Rendered as
PNG frames then encoded with ffmpeg (called by the caller).
"""
import os, sys
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "results", "campaign", "traces_closed")
V = os.path.join(ROOT, "results", "videos"); os.makedirs(V, exist_ok=True)
plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})
TEAL, AMBER, RED, GREEN, BLUE, GREY, PURPLE = "#0FA89B", "#E8A02A", "#D3343F", "#2FB85A", "#2C8CD6", "#7A7F8A", "#8155C6"

SEV_COLOR = {"normal": GREEN, "watch": AMBER, "contain": "#E8730A", "safe_mode": RED}

def render_run(aid, title, subtitle, participant="HUPA0001P"):
    ng = pd.read_csv(os.path.join(C, f"{participant}_{aid}_legacy_no_geco.csv"))
    gf = pd.read_csv(os.path.join(C, f"{participant}_{aid}_legacy_geco_full.csv"))
    n = len(gf); t = gf.t_min.values/60
    outdir = os.path.join(V, "frames_" + aid); os.makedirs(outdir, exist_ok=True)
    aw = gf[gf.attack_active]; a0 = aw.t_min.min()/60 if len(aw) else None; a1 = aw.t_min.max()/60 if len(aw) else None
    step = max(1, n//140)  # ~140 frames
    fidx = 0
    for k in range(1, n+1, step):
        fig = plt.figure(figsize=(12.8, 7.2)); fig.patch.set_facecolor("#0e1013")
        gs = fig.add_gridspec(3, 1, height_ratios=[2.2, 1.3, 0.7], hspace=0.34)
        ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1]); ax3 = fig.add_subplot(gs[2])
        for ax in (ax1, ax2, ax3):
            ax.set_facecolor("#15181d")
            for s in ax.spines.values(): s.set_color("#3a3f47")
            ax.tick_params(colors="#c8ccd2"); ax.grid(alpha=0.15)
        # glucose
        ax1.axhspan(70,180,color=GREEN,alpha=0.08)
        if a0 is not None: ax1.axvspan(a0,a1,color=AMBER,alpha=0.14)
        ax1.plot(t[:k], ng.true_glucose.values[:k], color=RED, lw=2, label="no GECO (attack reaches body)")
        ax1.plot(t[:k], gf.true_glucose.values[:k], color=TEAL, lw=2.2, label="GECO full (protected)")
        ax1.axhline(70,color="#9aa0ab",ls=":",lw=1)
        cut = gf[gf.cutoff];
        if len(cut) and cut.t_min.min()/60 <= t[k-1]:
            ax1.axvline(cut.t_min.min()/60,color=GREEN,ls="--",lw=1.6)
            ax1.text(cut.t_min.min()/60, 300, " cut-off", color=GREEN, fontsize=10, va="top")
        ax1.set_ylim(40,320); ax1.set_ylabel("glucose  mg/dL", color="#c8ccd2")
        ax1.set_xlim(0, t[-1]); ax1.legend(loc="upper left", facecolor="#15181d", edgecolor="#3a3f47", labelcolor="#e6e9ee", fontsize=10)
        ax1.set_title(title, color="#e6e9ee", fontsize=15, loc="left", pad=10)
        ax1.text(0.0, 1.14, subtitle, transform=ax1.transAxes, color=AMBER, fontsize=10.5)
        # delivery: commanded vs measured
        ax2.plot(t[:k], ng.measured_u.values[:k], color=RED, lw=1.6, label="delivered (no GECO)")
        ax2.plot(t[:k], gf.allowed_u.values[:k], color=BLUE, lw=1.4, label="authorised (GECO)")
        ax2.plot(t[:k], gf.measured_u.values[:k], color=TEAL, lw=1.8, label="delivered (GECO)")
        ax2.set_ylabel("insulin  U/step", color="#c8ccd2"); ax2.set_xlim(0,t[-1])
        ax2.legend(loc="upper left", facecolor="#15181d", edgecolor="#3a3f47", labelcolor="#e6e9ee", fontsize=9, ncol=3)
        # evidence channels (GECO)
        ax3.plot(t[:k], np.clip(gf.phys_score.values[:k],0,1), color=PURPLE, lw=1.4, label="physiology")
        ax3.plot(t[:k], np.clip(gf.prov_score.values[:k],0,1), color=BLUE, lw=1.4, label="provenance")
        ax3.plot(t[:k], np.clip(gf.act_score.values[:k],0,1), color=GREEN, lw=1.6, label="delivery")
        ax3.set_ylim(-0.05,1.1); ax3.set_ylabel("evidence", color="#c8ccd2"); ax3.set_xlim(0,t[-1])
        ax3.set_xlabel("hours", color="#c8ccd2")
        ax3.legend(loc="upper left", facecolor="#15181d", edgecolor="#3a3f47", labelcolor="#e6e9ee", fontsize=8, ncol=3)
        # severity chip
        sev = gf.severity.values[k-1]; kern = str(gf.kernel_severity.values[k-1])
        ax1.text(0.995, 0.06, f"GECO state: {sev.upper()}", transform=ax1.transAxes, ha="right",
                 color="white", fontsize=11, bbox=dict(boxstyle="round,pad=0.4", fc=SEV_COLOR.get(sev,GREY), ec="none"))
        fig.text(0.5, 0.015, "Non-clinical research bench — water/saline only — never connected to a person",
                 ha="center", color="#7A7F8A", fontsize=9)
        fig.savefig(os.path.join(outdir, f"f_{fidx:04d}.png"), dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig); fidx += 1
    return outdir, fidx

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "RF-10"
    meta = {
        "RF-10": ("Credentialed malicious controller", "Attacker holds a valid key — cryptography cannot help. The delivery twin + physical cut-off stop it."),
        "ACT-01": ("Compromised pump firmware over-delivers 2x", "The pump acknowledges the correct dose but pushes double. Only the independent balance sees the truth."),
        "COORD-03": ("Coherent digital compromise", "CGM + gateway keys + pump firmware all attacker-controlled. Physical mass measurement is the last honest witness."),
        "COORD-04": ("Everything forged, including the truth node", "The declared undetectable set: when every witness is compromised together, GECO abstains and states the impossibility."),
    }
    title, sub = meta[which]
    d, nf = render_run(which, title, sub)
    print(f"{which}: {nf} frames -> {d}")
