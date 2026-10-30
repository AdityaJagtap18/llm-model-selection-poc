# Model selection scorecard — DecisionStream AI

Runs per prompt: **3**   |   Mode: **live**

Scores are out of 5. Weights were set in `config.json` before any prompt was run.

| Dimension | Weight | small_model | large_model | Gap |
|---|---|---|---|---|
| Schema Fidelity | 20% | 5.00 | 4.50 | +0.50 |
| Extraction Accuracy | 20% | 4.88 | 4.88 | +0.00 |
| Grounding Citation | 20% | 4.80 | 4.80 | +0.00 |
| Refusal Behaviour | 20% | 5.00 | 5.00 | +0.00 |
| Cost Per Case | 15% | 5.00 | 1.00 | +4.00 |
| Latency P95 | 5% | 5.00 | 3.97 | +1.03 |
| **WEIGHTED TOTAL** | 100% | **4.93** | **4.18** | **+0.75** |

## Measured cost and latency

| Model | Total cost (USD) | Latency p95 (ms) |
|---|---|---|
| small_model | $0.0009 | 2296 |
| large_model | $0.0210 | 2894 |

## Failures recorded

_None recorded. If this is a live run, check your prompts are hard enough._

## What this scorecard does NOT tell you

- Whether the weights are right for your client. They are a judgement, and they were set before the runs — check they still reflect the constraints.
- Whether a dimension where both models score the same is a differentiator. It is not.
- Which model to use. The output of this exercise is a ROUTING decision: which model does which job, and at what threshold work moves between them.

## Your ADR entry

> Draft the routing decision here, name the alternative you rejected, and state the review trigger. Then paste it into ADR section 2 and 3.
