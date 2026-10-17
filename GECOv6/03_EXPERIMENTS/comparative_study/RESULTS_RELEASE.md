# Comparative study results

The main estimand applies identical clean-command tapes across arms. It measures delivery-authority interventions under fixed commands, not autonomous closed-loop efficacy. The smaller feedback/stop experiment is reported separately. All parameter units are synthetic; repeated seeds are averaged within parameter unit for confidence intervals.

Completed: 4608 main runs and 576 feedback/stop runs; 0 recorded failures. Main runs with any flagged out-of-domain physiology: 2108. Invalid trajectories remain present; glucose bands on those runs are mathematical summaries, not physiological predictions.

| Plant | Condition | Recovery | Full minus simple excess (U),95%CI | Full minus simple deficit (U),95%CI |
|---|---|---|---|---|
| geco_original | clean | manual | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | clean | supervised | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | excess_2x | manual | 0.010 [0.000,0.024] | -0.011 [-0.028,0.000] |
| geco_original | excess_2x | supervised | 0.010 [0.000,0.025] | -0.011 [-0.028,0.000] |
| geco_original | occlusion | manual | 0.000 [0.000,0.000] | -0.056 [-0.167,0.000] |
| geco_original | occlusion | supervised | 0.000 [0.000,0.000] | -0.047 [-0.163,0.015] |
| geco_original | stuck_on | manual | 0.137 [0.100,0.174] | -0.241 [-0.518,-0.007] |
| geco_original | stuck_on | supervised | 0.137 [0.100,0.174] | -0.281 [-0.567,-0.042] |
| geco_original | cgm_bias_40 | manual | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | cgm_bias_40 | supervised | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | cgm_missing | manual | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | cgm_missing | supervised | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | excess_bias_25 | manual | 0.010 [0.000,0.025] | -0.011 [-0.028,0.000] |
| geco_original | excess_bias_25 | supervised | 0.010 [0.000,0.023] | -0.011 [-0.027,0.000] |
| geco_original | excess_bias_report_mask | manual | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| geco_original | excess_bias_report_mask | supervised | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| hovorka_2004 | clean | manual | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| hovorka_2004 | clean | supervised | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| hovorka_2004 | excess_2x | manual | -0.003 [-0.019,0.013] | 0.149 [0.000,0.360] |
| hovorka_2004 | excess_2x | supervised | -0.003 [-0.019,0.013] | 0.206 [0.000,0.479] |
| hovorka_2004 | occlusion | manual | 0.000 [0.000,0.000] | 0.793 [0.102,1.637] |
| hovorka_2004 | occlusion | supervised | 0.000 [0.000,0.000] | 1.130 [0.140,2.378] |
| hovorka_2004 | stuck_on | manual | 0.085 [0.042,0.132] | -0.224 [-1.129,0.576] |
| hovorka_2004 | stuck_on | supervised | 0.085 [0.042,0.127] | -0.452 [-1.436,0.382] |
| hovorka_2004 | cgm_bias_40 | manual | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| hovorka_2004 | cgm_bias_40 | supervised | 0.000 [0.000,0.000] | 0.000 [0.000,0.000] |
| hovorka_2004 | cgm_missing | manual | 0.000 [0.000,0.000] | 0.150 [-0.003,0.404] |
| hovorka_2004 | cgm_missing | supervised | 0.000 [0.000,0.000] | 0.154 [-0.020,0.387] |
| hovorka_2004 | excess_bias_25 | manual | -0.003 [-0.019,0.013] | 0.149 [0.000,0.362] |
| hovorka_2004 | excess_bias_25 | supervised | -0.003 [-0.019,0.013] | 0.206 [0.000,0.470] |
| hovorka_2004 | excess_bias_report_mask | manual | 0.000 [0.000,0.000] | 0.016 [0.000,0.047] |
| hovorka_2004 | excess_bias_report_mask | supervised | 0.000 [0.000,0.000] | 0.049 [0.000,0.127] |

All arm, condition, plant and stop assumptions, including sham/oracle references, nulls and adverse differences, are retained in ARM_SUMMARIES and PAIRED_PARAMETER_UNIT_CI. A negative excess difference does not alone establish benefit: deficits, interruptions, false containment, recovery censoring and invalid physiology require joint interpretation.

Zero calibration statistical containment is a finite-sample fit criterion. Locked clean-run trips include identical local/quality rules and detector contributions; inspect full traces for attribution. Oracle delivery inhibition uses privileged fault labels and is an explanatory reference, not an achievable detection policy.

See METHODOLOGY.md, PREREGISTERED_SPEC.json, amendment records, all attempt ledgers and EXECUTION_MANIFEST.json for scope, parameter independence, code/config identities and failed-run accounting. No physical experiment, real sensor validation, clinical outcome or cybersecurity efficacy is established.
