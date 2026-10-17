"""Editable Graphviz method figures. All physical branches are explicitly prospective."""
from pathlib import Path
import json
import subprocess
R = Path(__file__).resolve().parents[1]
O = R / "04_PAPER/figures"
O.mkdir(exist_ok=True)
common = '''graph [rankdir=LR, bgcolor="white", pad="0.12", nodesep="0.30", ranksep="0.44", fontname="Arial", fontsize=12];
node [shape=box, style="filled", fillcolor="white", color="#334E61", fontname="Arial", fontsize=11, margin="0.13,0.09"];
edge [color="#38596A", fontname="Arial", fontsize=9, arrowsize=0.65];'''
diagrams = {
"signal_boundaries": r'''
request [label="Requested amount\nr_k (research U / interval)"];
auth [label="Authorization + recovery\na_k (research U / interval)"];
act [label="Virtual actuator\nemitted mass m_k (g)"];
plant [label="Physiological plant\noriginal family or Hovorka"];
sensor [label="Reported CGM\nobservation y_k"];
balance [label="Local balance indication\nsigned increment (g)"];
report [label="Received mass report\nmay differ from local indication"];
monitor [label="Monitoring policy\nfull / simple / sham", fillcolor="#E8F3F3"];
metric [label="Evaluator only\nexcess, deficit, glucose",fillcolor="#F4F4F4"];
request -> auth; auth -> act; act -> plant [label="latent emission / conversion\nsimulation only"];
plant -> sensor; sensor -> monitor [label="causal observation"];
act -> balance [label="measurement model"];
balance -> report; report -> monitor;
balance -> auth [label="common local budget",color="#AF642F"];
monitor -> auth [label="trip / verification",color="#AF642F"];
act -> metric [style=dashed]; plant -> metric [style=dashed];
{rank=same; balance; plant;} {rank=same; report; sensor;}
''',
"matched_experiment": r'''
unit [label="Synthetic parameter unit\n2 plants, 24 locked units each"];
exo [label="Matched meals and noise\n2 repeated seeds per unit"];
clean [label="Clean feedback reference\nfreeze requested-command tape"];
full [label="Full detector\nmanual / supervised recovery",fillcolor="#E8F3F3"];
simple [label="Simple mass residual\nmanual / supervised recovery",fillcolor="#E8F3F3"];
sham [label="Sham statistical detector\ncommon local and quality stops"];
oracle [label="Privileged fault-window oracle\nevaluator reference",fillcolor="#F4F4F4"];
paired [label="Same cap, local stop and observations\nfull 48 h; 8 conditions"];
out [label="Matched-clean excess AND deficit\ninterruption, recovery, glucose\nbootstrap parameter units"];
unit -> clean; exo -> clean;
clean -> full; clean -> simple; clean -> sham; clean -> oracle;
full -> paired; simple -> paired; sham -> paired; oracle -> paired; paired -> out;
{rank=same;full;simple;sham;oracle;}
''',
"recovery_states": r'''
run [label="RUN\nnormal bounded authorization",fillcolor="#E8F3F3"];
latched [label="LATCHED\ncommanded delivery = 0",fillcolor="#FFF2CC"];
verify [label="VERIFY\n3 capped requests\naggregate mass agreement"];
probation [label="PROBATION\n6 capped intervals"];
run -> latched [label="observed trip\nat interval end"];
latched -> verify [label="fixed operator slot + 30 min elapsed\n6 quiet readings + current CGM"];
verify -> probation [label="verification passes"];
probation -> run [label="probation completes"];
verify -> latched [label="trip / failed verification",color="#AF642F"];
probation -> latched [label="new trip",color="#AF642F"];
latched -> run [label="manual arm: same release gate\nwithout verification/probation",style=dashed];
note [shape=plaintext,label="Recovery cannot read the fault label or end time.\nNo accumulated catch-up delivery.\nPhysical flow can persist after a commanded latch."];
{rank=same;latched;note;}
''',
"physical_measurement": r'''
node [fillcolor="#FFF2CC"];
outlet [label="Defined water/saline outlet\nM01–M02"];
balance [label="Raw signed balance indication\nforce isolation + blank trials\nM03, M05–M06"];
temperature [label="Separate sample temperature\nfluid identity + density\nM04"];
reconstruct [label="Validated delivery reconstruction\ncorrections, delay, uncertainty\nM07–M09"];
reference [label="Independent calibrated reference\nmethod selection pending\nM07"];
logger [label="Synchronized native records\nclock transform + time marker\nM10"];
virtual [label="Explicit physical-to-model mapping\nvirtual-patient input"];
stop [label="Decision, electrical stop, cessation\npost-stop flow + recovery\nM11–M16"];
outlet -> balance; balance -> reconstruct; temperature -> reconstruct;
reference -> reconstruct [label="validation comparison"];
reconstruct -> virtual; balance -> logger; logger -> stop;
{rank=same;temperature;reference;balance;}
'''
}
receipts=[]
for name, body in diagrams.items():
    dot = O / f"{name}.dot"
    dot.write_text("digraph GECO {\n" + common + "\n" + body + "\n}\n")
    for fmt in ("svg", "pdf", "png", "plain"):
        subprocess.run(["/opt/homebrew/bin/dot", "-Gdpi=180", f"-T{fmt}", str(dot), "-o", str(O / f"{name}.{fmt}")], check=True)
    receipts.append({"name":name,"source":str(dot.relative_to(R)),"evidence":"CONCEPTUAL_PENDING" if name=="physical_measurement" else "IMPLEMENTED_SIMULATION_METHOD", "editable_formats":["dot","svg"],"physical_performance_claim":False})
(O/"METHOD_FIGURE_RECEIPT.json").write_text(json.dumps(receipts,indent=2))
print("Built",len(diagrams),"method figures")
