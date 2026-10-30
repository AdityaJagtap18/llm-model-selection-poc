"""
exercise_review.py — READ AND JUDGE. No typing required.

WHO THIS IS FOR
---------------
Everyone. If you do not write Python, this is your part of the lab and it is
not a consolation prize — reviewing someone else's inference code is closer
to the real Forward Deployed Engineer job than writing it.

WHAT TO DO
----------
Below is a working model-calling module. It runs. It returns answers. It
would pass a casual code review.

It contains SEVEN defects. Every one of them is a thing that has actually
gone wrong in a production AI service.

  1. Read the code.
  2. Write down each defect: the line, what is wrong, what it costs.
  3. For each one, say WHICH SPRINT 0 DECISION it breaks.
     (Hint: your ADR sections 2, 4, 5 and 6 all get broken here.)

Do not scroll to the bottom until you have found at least five. The answers
are at the end of this file, and reading them early wastes the exercise.

Scoring for the defence:
    5 or more found, with the cost named  ->  solid
    all 7, with the ADR section named     ->  senior
"""

import os
import json
import requests


API_KEY = "sk-proj-8f3a2b91d4e7c05a1e6b3f88d2c47a09"          # (1)
ENDPOINT = "https://prod-foundry-weu.services.ai.azure.com"     # (2)


def call_model(document_text, question):
    """Ask the model a question about a case document."""

    prompt = f"""You are a claims assistant. Answer the question about the
document below.

Document:
{document_text}

Question: {question}

Give your best answer."""                                        # (3) (4)

    response = requests.post(
        f"{ENDPOINT}/models/chat/completions",
        headers={"api-key": API_KEY},
        json={
            "model": "gpt-4o-mini",                              # (5)
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,                                  # (6)
            "max_tokens": 2000,
        },
    )

    answer = response.json()["choices"][0]["message"]["content"]

    print(f"Model answered: {answer}")                           # (7)
    return answer


def assess_claim(claim_folder):
    """Run the standard questions over every document in a claim."""
    results = {}
    for filename in os.listdir(claim_folder):
        with open(os.path.join(claim_folder, filename)) as f:
            text = f.read()
        results[filename] = {
            "total": call_model(text, "What is the total repair estimate?"),
            "date": call_model(text, "What is the incident date?"),
            "liability": call_model(text, "Has the third party admitted liability?"),
        }
    return results


if __name__ == "__main__":
    out = assess_claim("./claims/CLM-2026-04471")
    print(json.dumps(out, indent=2))


# ==========================================================================
#
#                    STOP. Have you written down five?
#
# ==========================================================================
#
#
#
#
#
#
#
#
#
#
#
#
# ANSWERS
# -------
#
# (1) A live API key hardcoded in source.
#     Cost: it is now in version control, in every clone, in every CI log,
#     and in the laptop backup of everyone who checked the repo out. Keys
#     grant full access to the resource and cannot be scoped to one action.
#     Breaks: ADR section 4 — "every service authenticates using a managed
#     identity; no credentials in application configuration".
#     Fix: managed identity, or Key Vault read at runtime.
#
# (2) The production endpoint hardcoded next to it.
#     Cost: there is no way to run this against a test environment without
#     editing code. Somebody will test against production. They always do.
#     Breaks: ADR section 2 — deployment targets come from config.
#
# (3) No source boundary and no delimiters around the document.
#     Cost: the model cannot tell your instructions from text that arrived
#     inside a customer's PDF. This is how prompt injection works, and the
#     document here is untrusted by definition.
#     Breaks: ADR section 6 — the injection control. Compare with prompt P10
#     in this lab: the same code, with delimiters, refuses the injection.
#
# (4) No refusal rule, no output contract, and "give your best answer".
#     Cost: the model is being explicitly told to produce something rather
#     than admit a gap. This is prompt P09 as a code defect — a plausible
#     answer where there is no answer. It is the single most expensive
#     failure mode in a decisioning system because nothing errors.
#     Breaks: ADR section 2 — structured output; section 6 — explainability.
#     Fix: a schema, and "if the value is not present, return not_found".
#
# (5) The model name as a string literal in the call.
#     Cost: when that deployment is retired, this is not a one-line change.
#     It is a change request, a re-test and a re-approval in every service
#     that named it. Also: the code never records which version actually
#     answered, so no decision can be reproduced.
#     Breaks: ADR section 2 and section 8 — the model-version review trigger
#     cannot fire if nobody logged the version.
#
# (6) temperature=0.7 on an extraction task.
#     Cost: the same document produces different numbers on different runs.
#     For a creative task that is a feature. For extracting a repair total
#     from a claim file it means the audit record cannot be reproduced, and
#     two handlers can see two different figures for the same claim.
#     Breaks: ADR section 5 — reproducibility of the decision record.
#
# (7) The answer is printed and returned. Nothing else happens.
#     Cost: no audit record, no citation, no token accounting, no latency
#     measurement, no schema validation, and no ordering guarantee. Also the
#     print statement puts customer data into stdout, which on most platforms
#     means into a log aggregator, which may sit outside your region.
#     Breaks: ADR section 5 — the audit record is written BEFORE the result
#     is released; and section 6 — residency.
#
# BONUS, if anyone found them:
#
# (8) No error handling at all. A 429 or a 500 becomes a KeyError on
#     ["choices"], which surfaces as a crash rather than a retryable signal.
#
# (9) assess_claim calls the model three times per document with no
#     idempotency key and no concurrency control. On a 30-document claim
#     that is 90 sequential calls, and a retry duplicates the lot.
#
# (10) The liability question is asked of every document, including ones
#      that could not possibly contain the answer. Cost is real: you pay
#      per token, and you have multiplied your exposure to defect (4).
#
# ==========================================================================
