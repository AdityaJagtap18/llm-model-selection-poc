# Sprint 1 · Day 11 Lab — Model Selection for DecisionStream AI

**Forward Deployed Engineer Academy — Sprint 1 lab**

Ten enterprise prompts. Two models. One weighted scorecard. One routing decision
for your ADR.

---

## Before anything else: this lab runs offline

```bash
python3 run_lab.py
```

No Azure account. No API key. No packages to install. The offline lab is pure
standard library, so that command works the moment you have Python.

That is deliberate. Nobody sits out today because their subscription is not
provisioned, and nobody spends the session debugging authentication instead of
thinking about model selection.

**The supported version is Python 3.12** — that is what this kit is built and
tested against. See [Prerequisites](#prerequisites) below if you do not have it.

When your Azure access is live, the same command runs against real models — see
**LIVE mode** below. Nothing else changes: same prompts, same graders, same
scorecard. You point it at a resource and choose an auth mode in `.env`.

---

## Prerequisites

### What you need, and when

| # | Requirement | Needed for | Blocking? |
|---|---|---|---|
| 1 | **Python 3.12** | Everything | **Yes** |
| 2 | A terminal and a text editor (VS Code) | Everything | Yes |
| 3 | ~200 MB free disk | The venv, for LIVE mode only | No |
| 4 | `pip install -r requirements.txt` in a venv | LIVE mode only | No |
| 5 | An **Azure OpenAI resource** + 2 model deployments | LIVE mode only | No |
| 6 | **Azure CLI** (`az`) | Keyless auth + Bicep only | No |
| 7 | An Azure role assignment on that resource | Keyless auth only | No |

**Rows 3–7 are not needed to complete this lab.** Everything that is assessed —
the ten prompts, the scorecard, the ADR entry, the review exercise — runs
offline on row 1 alone. If your Azure access is not ready, you are not behind.

### Verify what you have

```bash
python3.12 --version        # want: Python 3.12.x
```

If that prints a version, skip to [Set up the environment](#set-up-the-environment).
If it says "command not found", install it below.

---

## Installing Python 3.12

Pick the row for your machine. All three give you the same thing.

### macOS

| Method | Command | Notes |
|---|---|---|
| **Official installer** | Download from [python.org/downloads/macos](https://www.python.org/downloads/macos/) | Universal2 — works on both Apple Silicon and Intel. Easiest if you have no package manager. |
| **Homebrew** | `brew install python@3.12` | Then `brew link python@3.12` if `python3.12` is not found. |
| **uv** (fastest) | `curl -LsSf https://astral.sh/uv/install.sh \| sh`<br>`uv python install 3.12` | Downloads a self-contained CPython. No admin rights needed. |

> **Apple Silicon warning — this one is real.** If you already have a Python at
> `/usr/local/bin`, it may be an **x86_64** build running under Rosetta, and some
> wheels will either fail to install or install the wrong architecture. Check:
>
> ```bash
> python3.12 -c "import platform; print(platform.machine())"
> ```
>
> On an M-series Mac you want **`arm64`**. If you get `x86_64`, use the
> Homebrew or uv route above, which install native builds to `/opt/homebrew`
> or `~/.local` respectively.

### Windows

| Method | Command | Notes |
|---|---|---|
| **Official installer** | Download from [python.org/downloads/windows](https://www.python.org/downloads/windows/) | **Tick "Add python.exe to PATH"** on the first screen. Nearly every "python is not recognised" problem is this box. |
| **winget** | `winget install Python.Python.3.12` | Adds it to PATH for you. |

Use `py -3.12` instead of `python3.12` in every command below if the launcher is
what you have.

### Linux (Ubuntu / Debian)

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

`python3.12-venv` is a separate package on Debian-family distros and the venv
step fails without it.

### Confirm

```bash
python3.12 --version
python3.12 -c "import platform; print(platform.machine())"
```

### "I installed it and the command is still not found"

Almost always PATH, not a failed install. Find where it actually landed:

```bash
ls ~/.local/bin/python3.12          # uv
ls /opt/homebrew/bin/python3.12     # Homebrew, Apple Silicon
ls /usr/local/bin/python3.12        # Homebrew on Intel, or python.org
ls /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12   # python.org
```

Then either add that directory to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

…or skip PATH entirely and use the full path once, to build the venv:

```bash
~/.local/bin/python3.12 -m venv .venv
```

That second option is worth knowing: **after the venv exists, PATH stops
mattering.** `.venv/bin/python` is pinned to the interpreter that created it, so
every command in this README works whether or not `python3.12` is on your PATH.

---

## Set up the environment

The offline lab needs nothing installed. Do this anyway if you intend to reach
LIVE mode, and do it now rather than mid-session.

```bash
cd DecisionStream_Sprint1_Day11_Lab

python3.12 -m venv .venv                     # 1. create
.venv/bin/pip install -r requirements.txt    # 2. install (LIVE mode deps)
.venv/bin/python run_lab.py --check          # 3. prove it
```

On Windows the paths differ:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run_lab.py --check
```

**Run everything through `.venv/bin/python`, not a bare `python3`.** Prefixing
the path is what makes the environment take effect — there is nothing else to
"enable". If you would rather not type it each time, activate the venv for your
shell session:

```bash
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\Activate.ps1     # Windows PowerShell
```

Your prompt gains a `(.venv)` prefix, and `python` now means the venv's Python.
`deactivate` ends it. Activation is per-terminal — a new tab starts outside it,
which is the usual reason a command that worked ten minutes ago suddenly cannot
find `openai`.

Verify you are in the right interpreter at any time:

```bash
python -c "import sys; print(sys.executable)"   # should be inside .venv
```

> `.venv/` and `.env` are both in `.gitignore`. Do not commit either — one is
> 200 MB of platform-specific binaries, the other holds your Azure key.

---

## Everyone has a part in this lab

| If you are… | Your part | File |
|---|---|---|
| Comfortable in Python | Run the harness, extend the graders, add a third model | `run_lab.py`, `scorecard.py` |
| Not writing Python today | Find the seven defects in a working module | `decisionstream_lab/exercise_review.py` |
| Owning the decision | Set the weights, read the scorecard, draft the ADR entry | `config.json`, `out/scorecard.md` |

The review exercise is not a consolation prize. On a client site you will review
someone else's inference code far more often than you write your own, and every
defect in that file has actually happened in production.

---

## What to do, in order

### 1 · Set the weights FIRST (10 minutes, whole pod)

Open `config.json`. The `weights` block decides the outcome, so it is set before
any prompt runs and it is written down where everyone can see it.

```json
"weights": {
  "schema_fidelity":     0.20,
  "extraction_accuracy": 0.20,
  "grounding_citation":  0.20,
  "refusal_behaviour":   0.20,
  "cost_per_case":       0.15,
  "latency_p95":         0.05
}
```

They must sum to 1.0 — the lab refuses to run otherwise.

Argue about these. For a regulated insurer, refusal behaviour at 20% is
defensible. For a high-volume internal back-office task it is probably not.
**Write one line per weight saying where it came from.** A weight from habit is
where bias enters an apparently objective process.

> Changing weights after seeing results is not analysis. It is writing down the
> answer you already had.

### 2 · Check your environment

```bash
python3 run_lab.py --check
```

### 3 · Run it

```bash
python3 run_lab.py --runs 3
```

Three runs per prompt. The spread matters as much as the average — a model that
is right two times out of three is not a 67% model, it is an unreliable one.

Useful flags:

```bash
python3 run_lab.py --family compliance     # just P08–P10
python3 run_lab.py --family extraction --family narrative
```

### 4 · Read the output

Written to `out/`:

- **`scorecard.md`** — the weighted scorecard, ready to paste into your ADR
- **`scorecard.csv`** — the same numbers for your own analysis
- **`runs.json`** — every call: full text, tokens, latency, grade, notes

Then read **`INTERPRETING_RESULTS.md`** — what each number means, the six traps
in them, and how to turn the scorecard into a routing decision.

### 5 · Do the review exercise (parallel, 20 minutes)

```bash
# just open it and read — do not run it, it is deliberately broken
decisionstream_lab/exercise_review.py
```

### 6 · Write the ADR entry (15 minutes)

The bottom of `scorecard.md` has the three questions. The output of today is a
**routing decision**, not a favourite model.

---

## The ten prompts

| ID | Family | What it tests |
|---|---|---|
| P01 | extraction | Single field with a page citation |
| P02 | extraction | Multiple fields at once |
| P03 | extraction | A table, and whether the parts sum to the stated total |
| P04 | extraction | Two documents disagree — does it surface both, or pick one? |
| P05 | narrative | A 120-word summary with citations |
| P06 | narrative | Describe an inconsistency without concluding |
| P07 | narrative | A handover note, to a length limit |
| P08 | compliance | A policy limit check with no recommendation |
| **P09** | compliance | **The gap test — a field that is not in the document** |
| **P10** | compliance | **The injection test — an instruction hidden in a footer** |

**P09 and P10 are the two that matter.** Most models look similar on P01–P08.
A model that scores well everywhere and fails P09 will produce a confident,
well-formatted, wrong answer in production — and nothing will throw an error.

---

## LIVE mode — running against real Azure OpenAI

Two steps, in this order. **Key first, because it is the quickest way to prove
the pipeline works. Then Entra ID, because a key is not an answer you would ship.**

The point of doing both is what does *not* change between them. The client, the
call, the prompts, the graders and the scorecard are identical. Only the
credential moves. If that is true in your code, going keyless is a deployment
task. If it is not, it is a rewrite — and you find that out the week before go-live.

### Step 0 · Install and point at your resource

If you have not already done [Set up the environment](#set-up-the-environment):

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # then edit it
```

In `.env` set your resource endpoint. Paste it in whatever form the portal gave
you — the lab normalises it and prints what it resolved to:

```bash
DS_MODE=live
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
```

Then put your **real deployment names** in `config.json` under `live_deployment`
(the `deployment` field stays as-is; it drives the offline mock table):

```json
"small_model": { "deployment": "gpt-4o-mini-bulk", "live_deployment": "gpt-5-mini", ... },
"large_model": { "deployment": "claude-reasoning", "live_deployment": "gpt-5",      ... }
```

> Check the names against the resource, not against this file:
> `az cognitiveservices account deployment list -n <resource> -g <rg> -o table`
> A wrong deployment name is a **404**, not a 400, which is why it gets mistaken
> for a broken URL.

### Step 1 · API key

```bash
# in .env
DS_AUTH_MODE=key
AZURE_OPENAI_API_KEY=<your-key>
```

```bash
.venv/bin/python run_lab.py --check     # wiring only, no calls, no cost
.venv/bin/python run_lab.py --probe     # ONE cheap call per deployment
.venv/bin/python run_lab.py --runs 3    # the real run
```

`--probe` exists so that an auth problem costs you two calls instead of sixty.
Run it every time you change anything about the connection.

**What a key actually is:** a bearer secret with full data-plane access to the
resource, no per-action scope, no per-user attribution, and manual rotation. In
the logs, every call in your organisation looks like the same caller. That is
the whole case against it, and it is why step 2 exists.

### Step 2 · Entra ID (keyless), via Bicep

Two files in `infra/`. Pick the one that matches what you already have:

| You have… | Use | What it does |
|---|---|---|
| No Azure OpenAI resource yet | `infra/main.bicep` | Creates the resource, both model deployments, and the role assignment |
| A resource with deployments already | `infra/rbac.bicep` | **Only** adds the role assignment. Touches nothing else. |

```bash
# Your own object ID — this is who the role gets granted to
PRINCIPAL=$(az ad signed-in-user show --query id -o tsv)

# Path A — nothing exists yet
az deployment group create -g <rg> -f infra/main.bicep \
  -p aoaiName=<globally-unique-name> principalId=$PRINCIPAL allowKeyAuth=true

# Path B — you already have a resource
az deployment group create -g <rg> -f infra/rbac.bicep \
  -p aoaiName=<your-resource> principalId=$PRINCIPAL
```

Then switch the lab over — **this is the entire code change, and it is not code**:

```bash
# in .env
DS_AUTH_MODE=keyless
# and delete AZURE_OPENAI_API_KEY. Leaving a dead key in .env is how people
# convince themselves they went keyless when they did not.
```

```bash
az login
.venv/bin/python run_lab.py --probe
.venv/bin/python run_lab.py --runs 3
```

**Then prove it.** Set `allowKeyAuth=false` (or run `rbac.bicep` with
`disableKeyAuth=true` and apply the printed command) and re-run. Keys are now
refused at the resource. Your keyless run still works. That is the demonstration
— not the config file, the fact that one path died and the other did not.

Three things that will bite, in the order they usually do:

1. **RBAC takes a few minutes to propagate.** A 403 straight after the
   deployment is usually just impatience. Wait, then re-probe.
2. **`customSubDomainName` is required for Entra ID.** Without it the token
   audience cannot be resolved and every keyless call 401s. Both Bicep files set
   it; a resource made by hand in the portal may not have it.
3. **The role must be on *you*, not on the resource group's default.**
   `Cognitive Services OpenAI User` is the least privilege that can run
   inference — it cannot read keys, deploy models, or delete the resource.

### What was verified, and what it found

The old version of this section told you to check the docs. So we did, and the
check found two defects in this lab's own first draft. Both are fixed in
`provider.py`; both are exactly the failure mode the instruction was warning about.

Against **Microsoft Learn, "Azure OpenAI SDK language support", updated
2026-07-20**:

| Thing | The draft had | Current docs say |
|---|---|---|
| Client | `OpenAI(base_url=...)` | ✅ correct — plain `OpenAI`, **not** `AzureOpenAI` |
| `api_version` | passed | **No longer required.** The v1 API is GA |
| Entra scope | `https://cognitiveservices.azure.com/.default` | ❌ **moved** to `https://ai.azure.com/.default` |
| Entra token | `api_key=token()` — called once | ❌ **pass the provider itself**: `api_key=token_provider`. The SDK refreshes it. A pinned token dies mid-run |
| SDK floor | unpinned | `openai >= 1.106.0` to pass a token provider as `api_key` |
| Base URL | free-form | must end `/openai/v1/` — a 404 is usually this |

The second and fourth rows are the ones that matter. A one-shot `token()` works
perfectly in a ten-minute lab and fails in production at the one-hour mark, which
is the worst possible place on the difficulty/consequence curve.

**This is Pattern 1 with the receipt attached.** Because every vendor detail sits
in `provider.py`, both fixes were one file, and nothing above that layer knew. Go
and check it again before your own run. It will have moved again.

### Two things still to verify yourself

**1. Model availability and quota are per region.** `gpt-5-mini` / `gpt-5` are
this lab's defaults and they are *parameters*, not recommendations. Confirm what
your region and subscription will actually give you:
`az cognitiveservices account list-models -n <resource> -g <rg> -o table`

**2. The prices in `config.json` are illustrative.** Look up current pricing for
your region and deployment type. Never quote a number from a training file to a
client.

### A note on "Converse API"

The curriculum lists *"Converse API: unified interface across models"*. Converse
is the AWS Bedrock name for that idea. On Azure the equivalent is the **Azure AI
Model Inference API**, reached through the Foundry `/models` endpoint, which lets
you call different deployed models with one schema by naming the deployment in
the request body.

The **idea** is what matters and it is identical: one call site, deployment names
in config, swap models without touching the code above. `provider.py` is that
idea implemented — and it is why swapping models in this lab is a config change,
and why swapping *auth* is a `.env` change.

---

## What this lab does not do

- It does not tell you which model to use. It produces evidence for a routing
  decision you make and sign.
- It does not test everything. There is no multi-turn, no tool use, no long
  context, no non-English documents. Add prompts for whatever your client
  actually does.
- It does not measure quality on your data. The mock documents are synthetic.
  Real evaluation needs a gold set marked by someone who knows the domain.

---

## Files

```
run_lab.py                        the command you run
config.json                       weights, deployments, prices — all decisions
requirements.txt                  LIVE mode deps (mock mode needs none)
INTERPRETING_RESULTS.md           how to read the scorecard (read after the run)
.env.example                      LIVE mode template (endpoint + auth mode)
.gitignore                        keeps .env and .venv out of git
infra/
  main.bicep                      new resource + deployments + RBAC
  rbac.bicep                      RBAC only, for a resource you already have
decisionstream_lab/
  provider.py                     one interface, many models (the swap point)
  prompts.py                      the 10 prompts + gold answers
  mock_responses.py               offline documents and canned answers
  scorecard.py                    grading, then weighting — kept separate
  exercise_review.py              READ AND JUDGE — seven planted defects
out/                              scorecard.md · scorecard.csv · runs.json
```

---

## Before you present

- [ ] Weights set before the run, with a reason written for each
- [ ] Three runs per prompt, spread recorded
- [ ] You can explain what happened on P09 and P10 in one sentence each
- [ ] At least five of the seven review defects found
- [ ] A routing decision drafted: which model does which job, and the threshold
- [ ] You can name the dimension you are least confident scoring
