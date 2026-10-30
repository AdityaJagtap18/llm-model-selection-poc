"""
run_lab.py — the command you actually run.

    python run_lab.py                 # everything, mock mode
    python run_lab.py --runs 3        # three runs per prompt, record the spread
    python run_lab.py --family compliance
    python run_lab.py --check         # environment check only

Outputs, written to ./out/:
    runs.json        every call: text, tokens, latency, grade
    scorecard.md     the weighted scorecard, ready to paste into the ADR
    scorecard.csv    the same numbers for your own analysis
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from statistics import mean, pstdev

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "decisionstream_lab"))

from provider import (build_providers, normalise_base_url, normalise_account_url,  # noqa: E402
                      resolve_endpoint, resolve_api_key, resolve_auth_mode,
                      resolve_api_version, resolve_default_deployment,
                      default_scope_for_route)
from prompts import PROMPTS, SYSTEM, build_user_message   # noqa: E402
from mock_responses import get_doc            # noqa: E402
from scorecard import grade, build_scorecard, DIMENSIONS  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)


def load_dotenv(path: Path) -> list[str]:
    """
    Minimal .env reader — stdlib only, on purpose.

    Mock mode must keep its promise that `python3 run_lab.py` works with
    nothing installed, so the lab does not take a python-dotenv dependency
    just to read six lines. Real values already in the environment WIN, so
    `export` and `--check` behave the way a shell user expects.
    """
    loaded: list[str] = []
    if not path.exists():
        return loaded
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return loaded


def load_config(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def validate_weights(cfg: dict) -> list[str]:
    """
    Check the weights BEFORE any model is called.

    scorecard.py enforces the same invariant, but it only gets to see the
    weights once every response is already in. In LIVE mode that means you
    have paid for a full run before being told the config was invalid.
    So the guard runs here, first, and the exit code is honest about it.
    """
    w = cfg.get("weights", {})
    problems: list[str] = []
    missing = [d for d in DIMENSIONS if d not in w]
    unknown = [k for k in w if k not in DIMENSIONS]
    if missing:
        problems.append(f"missing weight(s): {', '.join(missing)}")
    if unknown:
        problems.append(f"unknown weight(s): {', '.join(unknown)} "
                        f"(valid: {', '.join(DIMENSIONS)})")
    total = sum(w.values())
    if abs(total - 1.0) > 1e-6:
        problems.append(f"weights sum to {total:.3f}, must be 1.000")
    return problems


def check_env(cfg: dict) -> int:
    mode = os.environ.get("DS_MODE", cfg.get("mode", "mock")).lower()
    print(f"  mode                 : {mode}")
    print(f"  models configured    : {', '.join(cfg['models'])}")
    for n, m in cfg["models"].items():
        # Show the deployment that will ACTUALLY be called, not the mock one.
        # A learner who sees the wrong name here chases the wrong 404.
        # Same resolution order as build_providers — if these two ever disagree
        # the check is worse than useless, because it is confidently wrong.
        if mode == "live":
            dep = (m.get("live_deployment") or resolve_default_deployment()
                   or m["deployment"])
            src = ("config live_deployment" if m.get("live_deployment")
                   else "AZURE_OPENAI_DEPLOYMENT" if resolve_default_deployment()
                   else "config deployment")
            print(f"    - {n:<14} deployment={dep:<16} (from {src})")
        else:
            print(f"    - {n:<14} deployment={m['deployment']}")
    w = cfg.get("weights", {})
    problems = validate_weights(cfg)
    print(f"  weights sum          : {sum(w.values()):.3f} "
          f"({'OK' if not problems else 'INVALID'})")
    for p in problems:
        print(f"    ! {p}")
    if mode == "live":
        problems += check_live_env()
    else:
        print("  (mock mode: no Azure resources required)")
    return 1 if problems else 0


def check_live_env() -> list[str]:
    """Report the live wiring, and resolve the endpoint so a 404 is visible early."""
    problems: list[str] = []
    raw = resolve_endpoint()
    auth = resolve_auth_mode()
    api_version = resolve_api_version()
    print(f"  auth mode            : {auth}")
    print(f"  route                : "
          f"{'classic (api-version=' + api_version + ')' if api_version else 'v1 (no api-version)'}")

    if raw:
        print(f"  endpoint (from .env) : {raw}")
        if api_version:
            # Print the real POST target. The single most expensive failure in
            # this lab is a 404 that names a deployment when the URL was wrong,
            # so the URL goes on screen before any call is made.
            print(f"  resolved POST url    : {normalise_account_url(raw)}"
                  f"/openai/deployments/<deployment>/chat/completions"
                  f"?api-version={api_version}")
        else:
            resolved = normalise_base_url(raw)
            print(f"  resolved base_url    : {resolved}")
            if not resolved.endswith("/openai/v1/"):
                problems.append(f"base URL did not resolve to /openai/v1/: {resolved}")
    else:
        problems.append("AZURE_OPENAI_ENDPOINT is not set (see .env.example)")
        print("  endpoint             : MISSING")

    if auth == "key":
        key = resolve_api_key()
        print(f"  AZURE_OPENAI_API_KEY : {'set (' + str(len(key)) + ' chars)' if key else 'MISSING'}")
        if not key:
            problems.append("DS_AUTH_MODE=key but AZURE_OPENAI_API_KEY is not set")
    else:
        scope = os.environ.get("DS_ENTRA_SCOPE") or default_scope_for_route(api_version)
        print(f"  entra scope          : {scope}")
        print("  credential           : DefaultAzureCredential (run `az login` first)")

    for pkg, why in (("openai", "required for both auth modes"),
                     ("azure.identity", "required for keyless only")):
        try:
            __import__(pkg)
            print(f"  {pkg:<21}: installed")
        except ImportError:
            state = "MISSING"
            if pkg == "azure.identity" and auth == "key":
                state = "not installed (fine for key mode)"
            else:
                problems.append(f"{pkg} is not installed ({why}) — "
                                f"pip install -r requirements.txt")
            print(f"  {pkg:<21}: {state}")

    for p in problems:
        print(f"    ! {p}")
    return problems


class LiveCallError(RuntimeError):
    """A model call failed. Carries enough context to fix it without a traceback."""

    def __init__(self, prompt_id: str, model: str, detail: str):
        self.prompt_id, self.model, self.detail = prompt_id, model, detail
        super().__init__(f"{prompt_id} on {model}: {detail}")


def probe(cfg: dict) -> int:
    """
    One cheap call per model before committing to a full run.

    This is the step that turns 'it does not work' into a named cause, and it
    costs a handful of tokens instead of a whole scorecard.
    """
    print("\nProbing each deployment with one minimal call\n")
    try:
        providers = build_providers(cfg)
    except RuntimeError as exc:
        print(f"  could not build providers: {exc}")
        return 1

    bad = 0
    for name, prov in providers.items():
        res = prov.complete("You are a health check. Reply with the single word OK.",
                            "Reply with exactly: OK", max_tokens=16)
        if res.error:
            bad += 1
            print(f"  {name:<14} FAIL  deployment={prov.deployment}")
            print(f"                 {res.error}")
        else:
            print(f"  {name:<14} OK    deployment={prov.deployment} "
                  f"-> served by model_id={res.model_id} "
                  f"({res.total_tokens} tokens, {res.latency_ms:.0f} ms)")
            print(f"                 reply: {res.text.strip()[:60]!r}")
    print()
    if bad:
        print(f"{bad} deployment(s) failed. Fix these before running the lab.")
    else:
        print("All deployments answered. Safe to run the full lab.")
    return 1 if bad else 0


def run(cfg: dict, families: list[str] | None, n_runs: int) -> dict:
    providers = build_providers(cfg)
    selected = [p for p in PROMPTS if not families or p["family"] in families]
    print(f"\nRunning {len(selected)} prompts x {len(providers)} models x {n_runs} run(s)\n")

    runs: dict[str, list[dict]] = {name: [] for name in providers}
    detail: list[dict] = []

    for p in selected:
        doc = get_doc(p["doc"])
        user = build_user_message(p, doc)
        line = f"  {p['id']} {p['title']:<32}"
        for name, prov in providers.items():
            accs, lats = [], []
            best = None
            for i in range(n_runs):
                res = prov.complete(SYSTEM, user)
                if res.error:
                    # Stop on the FIRST failure. A scorecard averaged over failed
                    # calls looks like a bad model rather than a broken pipe, and
                    # in live mode every further prompt costs money for nothing.
                    raise LiveCallError(p["id"], name, res.error)
                g = grade(p, res.text)
                accs.append(g.accuracy)
                lats.append(res.latency_ms)
                if best is None:
                    best = (res, g)
                detail.append({
                    "prompt_id": p["id"], "model": name, "run": i + 1,
                    "accuracy": g.accuracy, "grounding": g.grounding,
                    "refusal": g.refusal, "schema_ok": g.schema_ok,
                    "latency_ms": res.latency_ms, "tokens": res.total_tokens,
                    "model_id": res.model_id, "notes": g.notes,
                    "text": res.text,
                })
            res, g = best
            runs[name].append({"prompt": p, "result": res, "grade": g})
            spread = f"±{pstdev(accs):.2f}" if n_runs > 1 else "     "
            flag = "  <-- " + g.notes[0] if g.notes else ""
            line += f" | {name}: {mean(accs):.2f}{spread}"
            if g.notes:
                line += flag
        print(line)

    return {"runs": runs, "detail": detail}


def write_report(cfg: dict, sc: dict, detail: list[dict], n_runs: int) -> None:
    (OUT / "runs.json").write_text(json.dumps(detail, indent=2))

    names = sc["order"]
    rows = []
    hdr = ["Dimension", "Weight"] + names + (["Gap"] if sc["gap"] else [])
    rows.append(hdr)
    for d in DIMENSIONS:
        r = [d.replace("_", " ").title(), f"{cfg['weights'][d]:.0%}"]
        r += [f"{sc['models'][n][d]:.2f}" for n in names]
        if sc["gap"]:
            r.append(f"{sc['gap'][d]:+.2f}")
        rows.append(r)
    tot = ["**WEIGHTED TOTAL**", "100%"] + \
          [f"**{sc['models'][n]['weighted_total']:.2f}**" for n in names]
    if sc["gap"]:
        tot.append(f"**{sc['gap']['weighted_total']:+.2f}**")
    rows.append(tot)

    md = ["# Model selection scorecard — DecisionStream AI", "",
          f"Runs per prompt: **{n_runs}**   |   Mode: **{os.environ.get('DS_MODE', cfg.get('mode','mock'))}**",
          "", "Scores are out of 5. Weights were set in `config.json` before any prompt was run.",
          ""]
    md.append("| " + " | ".join(rows[0]) + " |")
    md.append("|" + "---|" * len(rows[0]))
    for r in rows[1:]:
        md.append("| " + " | ".join(r) + " |")

    md += ["", "## Measured cost and latency", "",
           "| Model | Total cost (USD) | Latency p95 (ms) |", "|---|---|---|"]
    for n in names:
        md.append(f"| {n} | ${sc['models'][n]['_cost_usd']:.4f} | "
                  f"{sc['models'][n]['_latency_p95_ms']:.0f} |")

    md += ["", "## Failures recorded", ""]
    any_fail = False
    for n in names:
        f = sc["models"][n]["_failures"]
        if f:
            any_fail = True
            md.append(f"**{n}**")
            for x in sorted(set(f)):
                md.append(f"- {x}")
            md.append("")
    if not any_fail:
        md.append("_None recorded. If this is a live run, check your prompts are hard enough._")

    md += ["", "## What this scorecard does NOT tell you", "",
           "- Whether the weights are right for your client. They are a judgement, "
           "and they were set before the runs — check they still reflect the constraints.",
           "- Whether a dimension where both models score the same is a differentiator. It is not.",
           "- Which model to use. The output of this exercise is a ROUTING decision: "
           "which model does which job, and at what threshold work moves between them.",
           "", "## Your ADR entry", "",
           "> Draft the routing decision here, name the alternative you rejected, "
           "and state the review trigger. Then paste it into ADR section 2 and 3.", ""]

    (OUT / "scorecard.md").write_text("\n".join(md))

    with open(OUT / "scorecard.csv", "w") as f:
        for r in rows:
            f.write(",".join(x.replace("**", "") for x in r) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="DecisionStream model selection lab")
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--runs", type=int, default=1, help="runs per prompt (use 3 for the spread)")
    ap.add_argument("--family", action="append",
                    choices=["extraction", "narrative", "compliance"])
    ap.add_argument("--check", action="store_true", help="environment check only")
    ap.add_argument("--probe", action="store_true",
                    help="one cheap call per model, to prove auth works before a full run")
    ap.add_argument("--env", default=str(HERE / ".env"), help="path to the .env file")
    args = ap.parse_args()

    loaded = load_dotenv(Path(args.env))
    cfg = load_config(Path(args.config))
    print("DecisionStream AI — model selection lab")
    print("=" * 62)
    if loaded:
        print(f"  .env                 : loaded {len(loaded)} var(s) "
              f"({', '.join(loaded)})")

    if args.check:
        return check_env(cfg)
    rc = check_env(cfg)
    if rc != 0:
        print("\nStopping before the first model call — the environment is not ready.")
        print("Fix the items marked ! above, then re-run with --check.")
        return 1
    if args.probe:
        return probe(cfg)

    try:
        data = run(cfg, args.family, args.runs)
    except LiveCallError as exc:
        print(f"\n  ABORTED on {exc.prompt_id} / {exc.model}")
        print(f"  {exc.detail}")
        print("\nNo scorecard written — a scorecard averaged over failed calls "
              "would read as a bad model rather than a broken connection.")
        print("Run `python3 run_lab.py --probe` to test auth on its own.")
        return 1
    sc = build_scorecard(data["runs"], cfg)
    write_report(cfg, sc, data["detail"], args.runs)

    print("\n" + "=" * 62)
    print("WEIGHTED TOTALS")
    for n in sc["order"]:
        print(f"  {n:<16} {sc['models'][n]['weighted_total']:.2f} / 5.00   "
              f"(cost ${sc['models'][n]['_cost_usd']:.4f}, "
              f"p95 {sc['models'][n]['_latency_p95_ms']:.0f} ms)")
    if sc["gap"]:
        g = sc["gap"]["weighted_total"]
        print(f"\n  Gap: {g:+.2f}  ({sc['order'][0]} minus {sc['order'][1]})")
        if abs(g) < 0.25:
            print("  That is close enough to be a tie. Your tiebreak must be "
                  "stated explicitly — do not re-score until one wins.")
    print(f"\nWritten: {OUT/'scorecard.md'}")
    print(f"         {OUT/'scorecard.csv'}")
    print(f"         {OUT/'runs.json'}")
    print("\nNow open scorecard.md and answer the three questions at the bottom.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
