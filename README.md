# LLM Model Selection POC

> A Forward Deployed Engineering (FDE) proof of concept. This repository contains both the **pre-transformation** (before) and **post-transformation** (after) states of the solution, so the impact of the work can be seen side by side.

---

## 1. Overview

| Item | Details |
|------|---------|
| **POC Name** | LLM Model Selection POC |
| **Scenario** | DecisionStream AI, an AI-assisted UK motor-claims service (illustrative course scenario) |
| **Owner** | Aditya Jagtap |
| **Status** | Completed |
| **Program** | Forward Deployed Engineer Academy, Sprint 1 · Day 11 Lab |

**One-line summary:** Replaces "pick the model that feels best" with a repeatable, weighted scorecard that compares a small and a large model on ten claims prompts, so the output is a defensible routing decision instead of a favourite.

---

## 2. Problem Statement

An insurer is building DecisionStream AI to read claim files and return cited facts and short internal drafts for claims handlers. Larger models cost far more, and smaller ones may fail in ways that matter in a regulated setting. The team needs to decide which model does which job.

- **Subjective comparison:** trying a few prompts and judging by feel is not repeatable, and the criteria can be quietly adjusted after the results are seen.
- **Silent failures:** a model that invents a liability admission, or obeys an instruction hidden in a document footer, still returns well-formed JSON. Nothing throws an error, so the wrong fact reaches a handler.
- **Cost vs. safety trade-off:** routing everything to the biggest model overpays, and shipping a cheap model that fabricates facts is a compliance risk.

---

## 3. Pre-Transformation (Before)

The starting state is the evaluation kit as handed out: the harness, the ten prompts, the graders and the Bicep templates, with the weights set but **no recorded reasoning, no live run and no analysis**.

| Aspect | Current State |
|--------|---------------|
| Process | Run the harness offline (mock mode) against canned responses. Weights are present in `config.json` but nothing records where they came from. |
| Model / Tooling | `small_model` and `large_model` as mock placeholders (`gpt-4o-mini-bulk`, `claude-reasoning`); `provider.py` abstraction; Bicep templates in `infra/` |
| Cost | Illustrative per-1k-token prices only; no measured spend |
| Latency / Performance | Simulated (`mock_latency_ms`), not measured |
| Accuracy / Quality | Scored against canned answers, so not real model behaviour |
| Pain points | No evidence from real deployments. No written rationale for the weights, which is where bias can enter an apparently objective process. No routing decision. |

**Location in repo:** [Pre_Transformation/](Pre_Transformation/)

---

## 4. Post-Transformation (After)

The same kit, taken to a finished decision: weights justified in writing, a live run against real Azure OpenAI deployments, a recorded scorecard, and a project analysis.

| Aspect | New State |
|--------|-----------|
| Process | Weights fixed and justified **before** any prompt ran, then 10 prompts × 2 models × 3 runs executed in LIVE mode (60 recorded calls) |
| Model / Tooling | Live Azure OpenAI deployments: `gpt-4.1-mini` (small) and `gpt-4.1` (large), via the provider abstraction |
| Cost | Measured: **$0.0009** (small) vs **$0.0210** (large) for the run |
| Latency / Performance | Measured p95: **2296 ms** (small) vs **2894 ms** (large) |
| Accuracy / Quality | Both models tie on extraction, grounding and refusal behaviour; small leads on schema fidelity |
| Benefits | Evidence-backed routing decision, a per-weight rationale in `config.json`, a saved audit trail (`runs.json`) and a written analysis in `docs/` |

**Location in repo:** [Post-Transformation/](Post-Transformation/)

---

## 5. Before vs. After

| Metric | Pre-Transformation | Post-Transformation | Change |
|--------|--------------------|---------------------|--------|
| Weight rationale | None recorded | One line per weight in `config.json` | Added |
| Run mode | Mock (canned responses) | Live (Azure OpenAI), 60 recorded calls | Real model evidence |
| Measured cost | Illustrative prices only | $0.0009 small / $0.0210 large | Large is ~23× the small model |
| Measured latency (p95) | Simulated | 2296 ms small / 2894 ms large | Large is ~26% slower at p95 |
| Weighted score (out of 5) | Not from real models | 4.93 small / 4.18 large | Small +0.75 |
| Documentation | Lab README and interpretation guide | Plus `docs/project_analysis.md` | Added |

### Live scorecard (Post-Transformation)

| Dimension | Weight | small_model | large_model | Gap |
|---|---|---|---|---|
| Schema Fidelity | 20% | 5.00 | 4.50 | +0.50 |
| Extraction Accuracy | 20% | 4.88 | 4.88 | +0.00 |
| Grounding Citation | 20% | 4.80 | 4.80 | +0.00 |
| Refusal Behaviour | 20% | 5.00 | 5.00 | +0.00 |
| Cost Per Case | 15% | 5.00 | 1.00 | +4.00 |
| Latency P95 | 5% | 5.00 | 3.97 | +1.03 |
| **Weighted total** | 100% | **4.93** | **4.18** | **+0.75** |

Source: [Post-Transformation/out/scorecard.md](Post-Transformation/out/scorecard.md). The weights are from [Post-Transformation/config.json](Post-Transformation/config.json).

---

## 6. Approach

1. **Discover** – Frame the problem as a routing decision for a regulated insurer, where silent failures matter more than speed.
2. **Baseline** – Start from the offline kit: ten prompts over four synthetic claim documents, graders and a scorecard.
3. **Evaluate** – Set the weights first and write a reason for each. Compare the two models across six dimensions, with the P09 (gap test) and P10 (injection test) prompts as the key checks.
4. **Build** – Point `config.json` at real deployments and run in LIVE mode through `provider.py`, with API-key or keyless (Entra ID) auth.
5. **Measure** – Run three passes per prompt, record every call in `runs.json`, and read the scorecard.
6. **Hand off** – Draft the routing decision for the ADR and write up the analysis in `docs/project_analysis.md`.

### Model Selection Criteria

| Criterion | Weight | Why |
|---|---|---|
| Schema fidelity | 20% | Downstream handlers parse the output as structured data |
| Extraction accuracy | 20% | Core task correctness |
| Grounding / citation | 20% | A decision without a page citation can't be audited |
| Refusal behaviour | 20% | Fabrication or obeying an injection is a silent, high-consequence failure |
| Cost per case | 15% | Material at volume, but subordinate to correctness |
| Latency (p95) | 5% | Async back-office flow, not live chat |

---

## 7. Repository Structure

```
llm-model-selection-poc/
├── README.md
├── Pre_Transformation/               # "Before": the lab kit as handed out
│   ├── run_lab.py                    # the command you run
│   ├── config.json                   # weights, deployments, prices
│   ├── decisionstream_lab/           # provider, prompts, mock responses, scorecard, review exercise
│   ├── infra/                        # main.bicep, rbac.bicep
│   └── INTERPRETING_RESULTS.md
└── Post-Transformation/              # "After": the completed POC
    ├── run_lab.py
    ├── config.json                   # adds a rationale for every weight
    ├── decisionstream_lab/
    ├── infra/
    ├── out/                          # scorecard.md · scorecard.csv · runs.json
    ├── docs/project_analysis.md      # written analysis of the project and run
    └── INTERPRETING_RESULTS.md
```

---

## 8. Getting Started

### Prerequisites

- Python 3.12
- Offline (mock) mode needs nothing else: no Azure account, API key or packages
- LIVE mode only: an Azure OpenAI resource with two model deployments, `pip install -r requirements.txt`, and either an API key or Azure CLI plus the `Cognitive Services OpenAI User` role for keyless auth

### Setup

```powershell
cd Post-Transformation

py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run_lab.py --check

# LIVE mode only
copy .env.example .env      # then set DS_MODE, AZURE_OPENAI_ENDPOINT and the auth mode
```

Put your real deployment names under `live_deployment` in `config.json`. Never commit `.env`.

### Run

```powershell
# offline baseline (works for both folders)
python run_lab.py --runs 3

# live mode: one cheap call per deployment first, then the real run
.venv\Scripts\python run_lab.py --probe
.venv\Scripts\python run_lab.py --runs 3
```

Results are written to `out/`. Read `INTERPRETING_RESULTS.md` afterwards.

---

## 9. Results & Learnings

- **Key result:** The small model scored **4.93** against the large model's **4.18**. It ties on every quality dimension except schema fidelity, where it leads, and costs a fraction as much.
- **What worked:** Fixing and justifying the weights before the run. Keeping all vendor details in `provider.py`, so changing deployments and auth were config changes.
- **What didn't:** The scorecard is only as good as its graders. `docs/project_analysis.md` records that it scores only the first of the three runs per prompt and that some string-match graders mis-score correct answers, so the cost gap drives most of the result. Fixing the graders is the most useful follow-up exercise.
- **Recommendations:** Route bulk extraction work to the small model. Escalate to the large model on a machine-checkable condition (for example, invalid JSON or a `not_found` field). Confirm on a larger gold set before shipping.

> Caveats: the documents are four short synthetic ones, prices in `config.json` are illustrative, and no savings or customer outcome has been measured.

---

## 10. Next Steps

- [ ] Fix the scorecard so it uses all three runs, and review the graders flagged in the analysis
- [ ] Re-run the scorecard and confirm the routing decision still holds
- [ ] Build a domain-reviewed gold set from real (non-synthetic) claim documents
- [ ] Add prompts for multi-turn, tool use and long-context cases
- [ ] Record the routing decision, the rejected alternative and the review trigger in the ADR

---

## 11. Contact

Aditya Jagtap · adiraj2503@gmail.com
