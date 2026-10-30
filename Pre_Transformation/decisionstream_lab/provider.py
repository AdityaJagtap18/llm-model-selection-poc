"""
provider.py — one interface, many models.

WHY THIS FILE EXISTS
--------------------
The curriculum for today says "Converse API: unified interface across models".
Converse is the AWS Bedrock name. On Azure the equivalent idea is the
**Azure AI Model Inference API**, reached through the Foundry `/models`
endpoint, which lets you call different deployed models with one schema by
putting the deployment name in the request body.

The idea is identical and it is the idea that matters:

    ONE call site. Deployment names in config. Swap models without
    touching the code that uses them.

IMPORTANT — SDK CHOICE (verify before you rely on this)
-------------------------------------------------------
Microsoft has announced retirement of the standalone `azure-ai-inference`
beta SDK. Their published migration guidance points to the OpenAI SDK aimed
at the Azure OpenAI v1 endpoint. This lab therefore uses the OpenAI SDK shape
and keeps the vendor detail behind an adapter, so that when the SDK moves
again you change ONE file — this one.

That is not an accident of the lab. It is the whole lesson of Pattern 1.

And it has already paid for itself. Checking the docs (Microsoft Learn,
"Azure OpenAI SDK language support", updated 2026-07-20) against this file's
first draft found two things the draft had wrong:

    * the Entra scope had moved to https://ai.azure.com/.default
    * the token PROVIDER is passed as api_key, not a token — the draft
      called it once, which pins a token that expires mid-run

Both were fixed here, in one file, and nothing above this layer changed.
That is what the adapter bought. Check it again before your own live run;
the answer will have moved by the time you read this.

MODES
-----
MOCK  (default) — no Azure account needed. Deterministic canned responses.
                  Everybody in the pod can complete the lab.
LIVE            — real Azure OpenAI calls, either auth path:
                    DS_AUTH_MODE=key      an API key   (step 1 — quickest)
                    DS_AUTH_MODE=keyless  Entra ID     (step 2 — the answer)
                  Same client, same call. Only the credential changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Any


# --------------------------------------------------------------------------
# The result object every provider must return. Nothing above this layer
# knows which vendor produced it.
# --------------------------------------------------------------------------
@dataclass
class ModelResult:
    text: str
    model_id: str                 # what the API said it used, not what we asked for
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    stop_reason: str = "stop"
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def cost_usd(self, price_in_per_1k: float, price_out_per_1k: float) -> float:
        return (self.prompt_tokens / 1000.0) * price_in_per_1k + \
               (self.completion_tokens / 1000.0) * price_out_per_1k

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("raw", None)
        return d


class ModelProvider:
    """Base class. Both real and mock providers implement complete()."""

    def __init__(self, name: str, deployment: str, cfg: dict[str, Any]):
        self.name = name
        self.deployment = deployment
        self.cfg = cfg

    def complete(self, system: str, user: str, max_tokens: int = 900,
                 temperature: float = 0.0) -> ModelResult:
        raise NotImplementedError


# --------------------------------------------------------------------------
# MOCK provider — deterministic, offline, and deliberately imperfect.
#
# The canned answers are NOT all correct. Each model has its own failure
# profile so the scorecard produces a real comparison rather than a tie.
# --------------------------------------------------------------------------
class MockProvider(ModelProvider):

    def complete(self, system: str, user: str, max_tokens: int = 900,
                 temperature: float = 0.0) -> ModelResult:
        from mock_responses import lookup

        key = _prompt_key(user)
        canned = lookup(self.name, key)

        # Deterministic pseudo-latency so runs are repeatable but not identical
        seed = int(hashlib.sha256((self.name + key).encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        base = self.cfg.get("mock_latency_ms", 1200)
        latency = base * rng.uniform(0.75, 1.35)
        time.sleep(min(latency / 4000.0, 0.05))  # keep the lab quick

        text = canned["text"]
        return ModelResult(
            text=text,
            model_id=f"{self.deployment}@mock",
            prompt_tokens=max(1, len(system.split()) + len(user.split())),
            completion_tokens=max(1, len(text.split())),
            latency_ms=round(latency, 1),
            stop_reason=canned.get("stop_reason", "stop"),
        )


# --------------------------------------------------------------------------
# Endpoint handling.
#
# A 404 on a live run is almost always this: the base URL must end in
# /openai/v1/. Microsoft's own troubleshooting table says so. We accept every
# form a learner is likely to paste out of the portal and normalise it, then
# PRINT what we resolved, so the failure is visible before the call is made.
# --------------------------------------------------------------------------
V1_SUFFIX = "openai/v1/"


def normalise_account_url(raw: str) -> str:
    """Strip any route suffix a learner pasted, leaving the bare resource URL."""
    url = raw.strip().rstrip("/")
    for tail in ("/openai/v1", "/openai", "/models"):
        if url.endswith(tail):
            url = url[: -len(tail)]
            break
    return url


def normalise_base_url(raw: str) -> str:
    """Accept any portal/docs form of the endpoint, return the /openai/v1/ form."""
    return f"{normalise_account_url(raw)}/{V1_SUFFIX}"


def resolve_endpoint() -> str | None:
    return (os.environ.get("AZURE_OPENAI_ENDPOINT")
            or os.environ.get("DS_FOUNDRY_BASE_URL"))     # legacy name, still honoured


def resolve_api_key() -> str | None:
    return (os.environ.get("AZURE_OPENAI_API_KEY")
            or os.environ.get("DS_FOUNDRY_API_KEY"))      # legacy name, still honoured


def resolve_api_version() -> str | None:
    """
    Which of Azure's TWO data-plane routes to use.

    None  -> v1:      POST /openai/v1/chat/completions            (no api-version)
    set   -> classic: POST /openai/deployments/<name>/chat/completions?api-version=

    Not every resource serves both. A resource that only serves the classic
    route answers EVERY v1 request with 404 DeploymentNotFound — including for
    deployments that demonstrably exist. That error names the deployment, so it
    reads as "this model is missing" when the truth is "this route is missing".
    Learners will burn an hour redeploying models to fix a URL.
    """
    return os.environ.get("AZURE_OPENAI_API_VERSION", "").strip() or None


def resolve_default_deployment() -> str | None:
    """Fallback deployment for a config entry with no live_deployment."""
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip() or None


def resolve_auth_mode() -> str:
    """key | keyless. Explicit env wins; otherwise a key present means key mode."""
    mode = os.environ.get("DS_AUTH_MODE", "").strip().lower()
    if mode in ("key", "keyless"):
        return mode
    return "key" if resolve_api_key() else "keyless"


# Entra scope. VERIFIED against Microsoft Learn, "Azure OpenAI SDK language
# support", updated 2026-07-20: the v1 endpoint uses https://ai.azure.com/.default.
# The older https://cognitiveservices.azure.com/.default is what most blog posts
# and this lab's own first draft used. Overridable, because it will move again.
DEFAULT_ENTRA_SCOPE = "https://ai.azure.com/.default"

# The classic (api-version) route predates that change and still takes the
# older audience. Route and scope have to agree: the right token for the wrong
# audience is a 401, which reads exactly like a missing role assignment and
# sends people off to re-check RBAC that was never the problem.
CLASSIC_ENTRA_SCOPE = "https://cognitiveservices.azure.com/.default"


def default_scope_for_route(api_version: str | None) -> str:
    return CLASSIC_ENTRA_SCOPE if api_version else DEFAULT_ENTRA_SCOPE


# --------------------------------------------------------------------------
# LIVE provider — Azure OpenAI v1 API via the OpenAI SDK.
#
# WHAT WAS VERIFIED (Microsoft Learn, updated 2026-07-20) — do it again yourself:
#   * The client is the plain `OpenAI` one with base_url, NOT `AzureOpenAI`.
#   * The v1 API is GA and `api_version` is NO LONGER a required parameter.
#   * For Entra ID you pass the token provider AS the api_key. It is a callable
#     and the SDK refreshes the token. Needs openai >= 1.106.0.
#   * The scope is https://ai.azure.com/.default (it changed).
#   * `model` is your DEPLOYMENT name, not the model family name.
#
# Both auth paths build the SAME client and the SAME call. That is the point:
# going keyless is a credential change, not a code change.
# --------------------------------------------------------------------------
class AzureOpenAIProvider(ModelProvider):

    def __init__(self, name: str, deployment: str, cfg: dict[str, Any]):
        super().__init__(name, deployment, cfg)
        try:
            from openai import OpenAI, AzureOpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "LIVE mode needs the openai package: pip install -r requirements.txt"
            ) from exc

        raw = resolve_endpoint()
        if not raw:
            raise RuntimeError(
                "Set AZURE_OPENAI_ENDPOINT in .env (see .env.example). "
                "Example: https://my-resource.openai.azure.com/"
            )
        self.api_version = resolve_api_version()
        self.route = "classic" if self.api_version else "v1"
        self.account_url = normalise_account_url(raw)
        # What we will actually POST to — printed by --check so the URL is
        # visible BEFORE the call, not inferred from a 404 afterwards.
        self.base_url = (f"{self.account_url}/openai/deployments/<deployment>/"
                         f"chat/completions?api-version={self.api_version}"
                         if self.api_version else normalise_base_url(raw))
        self.auth_mode = resolve_auth_mode()

        # Only the CLIENT differs between the two routes. Everything below this
        # constructor — the call, the retry ladder, the result object — is
        # identical. Same reason the two auth modes share a code path.
        if self.auth_mode == "key":
            key = resolve_api_key()
            if not key:
                raise RuntimeError(
                    "DS_AUTH_MODE=key but AZURE_OPENAI_API_KEY is not set. "
                    "Either set the key, or switch to DS_AUTH_MODE=keyless."
                )
            # A key is a bearer secret with full data-plane access to the
            # resource. Fine for the first run today; replaced in step 2.
            self._client = (
                AzureOpenAI(api_key=key, azure_endpoint=self.account_url,
                            api_version=self.api_version)
                if self.api_version else
                OpenAI(api_key=key, base_url=self.base_url))
        else:
            try:
                from azure.identity import (  # type: ignore
                    DefaultAzureCredential, get_bearer_token_provider)
            except ImportError as exc:
                raise RuntimeError(
                    "DS_AUTH_MODE=keyless needs azure-identity: "
                    "pip install -r requirements.txt"
                ) from exc
            scope = os.environ.get("DS_ENTRA_SCOPE") or \
                default_scope_for_route(self.api_version)
            # NOTE the missing parentheses: the PROVIDER is passed, not a token.
            # Calling token() here would pin one token and the run would fail
            # the moment it expired. This is the whole difference.
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), scope)
            # The classic client has a dedicated argument for this. The v1
            # client takes the provider as api_key. Same idea, different name.
            self._client = (
                AzureOpenAI(azure_ad_token_provider=token_provider,
                            azure_endpoint=self.account_url,
                            api_version=self.api_version)
                if self.api_version else
                OpenAI(api_key=token_provider, base_url=self.base_url))

    # ----------------------------------------------------------------------
    # Model families differ on parameter names. gpt-5 era deployments reject
    # `max_tokens` (they want `max_completion_tokens`) and some reject any
    # non-default `temperature`. We try the standard call, then degrade —
    # once, deliberately, and we record what we dropped.
    # ----------------------------------------------------------------------
    def _create(self, system: str, user: str, max_tokens: int, temperature: float):
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        attempts = [
            {"max_tokens": max_tokens, "temperature": temperature},
            {"max_completion_tokens": max_tokens, "temperature": temperature},
            {"max_completion_tokens": max_tokens},
        ]
        last: Exception | None = None
        for kwargs in attempts:
            try:
                return self._client.chat.completions.create(
                    model=self.deployment,       # from config, never a literal
                    messages=messages, **kwargs), kwargs
            except Exception as exc:             # noqa: BLE001
                last = exc
                if not _is_unsupported_param(exc):
                    raise
        raise last  # type: ignore[misc]

    def complete(self, system: str, user: str, max_tokens: int = 900,
                 temperature: float = 0.0) -> ModelResult:
        t0 = time.perf_counter()
        try:
            r, used = self._create(system, user, max_tokens, temperature)
        except Exception as exc:                 # noqa: BLE001 - we want the message
            return ModelResult(
                text="", model_id=self.deployment, prompt_tokens=0,
                completion_tokens=0, latency_ms=(time.perf_counter() - t0) * 1000,
                stop_reason="error",
                error=explain_azure_error(exc, self),
            )

        latency = (time.perf_counter() - t0) * 1000
        usage = getattr(r, "usage", None)
        choice = r.choices[0]
        return ModelResult(
            text=choice.message.content or "",
            model_id=getattr(r, "model", self.deployment),   # what it ACTUALLY used
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            latency_ms=round(latency, 1),
            stop_reason=getattr(choice, "finish_reason", "stop") or "stop",
            raw={"params": sorted(used), "auth_mode": self.auth_mode},
        )


# Kept so older notes and any learner branch that imported the old name still work.
FoundryProvider = AzureOpenAIProvider


def _is_unsupported_param(exc: Exception) -> bool:
    m = str(exc).lower()
    return ("unsupported" in m or "unrecognized" in m or "not supported" in m) and \
           ("max_tokens" in m or "max_completion_tokens" in m or "temperature" in m)


def _is_credential_error(exc: Exception) -> bool:
    """An azure-identity failure — no token was ever obtained, so there is no
    HTTP status to read. Matched by type name so we need not import the SDK."""
    seen, cur = set(), exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if type(cur).__name__ in {"ClientAuthenticationError",
                                  "CredentialUnavailableError"}:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def explain_azure_error(exc: Exception, prov: "AzureOpenAIProvider") -> str:
    """
    Turn an SDK exception into something a learner can act on.
    The mapping is Microsoft's own troubleshooting table, not folklore.
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    base = f"{type(exc).__name__}: {exc}"

    # DefaultAzureCredential prints every credential it tried — around 20 lines
    # of which one matters. Say the actionable thing first; keep the detail short.
    if _is_credential_error(exc):
        first = str(exc).strip().splitlines()[0][:160]
        return ("no Entra token could be obtained — you are not signed in. "
                "Run `az login` (and `az account set --subscription <id>` if you "
                "have more than one). If you meant to use a key instead, set "
                "DS_AUTH_MODE=key and AZURE_OPENAI_API_KEY in .env.  "
                f"[{type(exc).__name__}: {first}]")
    if status in (401, 403):
        if prov.auth_mode == "key":
            hint = ("key rejected. Check AZURE_OPENAI_API_KEY, and check the "
                    "resource does not have local auth disabled "
                    "(disableLocalAuth=true means keys are OFF by design).")
        else:
            hint = ("identity rejected. Run `az login`, confirm the role "
                    "'Cognitive Services OpenAI User' is assigned to YOU on this "
                    "resource, and allow a few minutes for RBAC to propagate.")
        return f"{status} {hint}  [{base}]"
    if status == 404:
        if prov.route == "v1":
            # Ordered by how often it is actually the cause. The wrong-route
            # case is FIRST because the error text names the deployment and so
            # argues persuasively for the wrong answer.
            return (f"404 on the v1 route (resolved to {prov.base_url}). "
                    f"Either this resource does not serve /openai/v1/ at all — "
                    f"set AZURE_OPENAI_API_VERSION=2024-12-01-preview in .env to "
                    f"use the classic route, and note that a resource without v1 "
                    f"404s EVERY deployment name including ones that exist — or "
                    f"the deployment '{prov.deployment}' really is missing.  [{base}]")
        return (f"404 on the classic route. The route is right, so the "
                f"deployment name '{prov.deployment}' does not exist on this "
                f"resource. List what does: curl -H \"api-key: $AZURE_OPENAI_API_KEY\" "
                f"\"{prov.account_url}/openai/deployments?api-version=2022-12-01\" "
                f"— and if that returns an empty list, trust the portal over it. "
                f"Fix live_deployment in config.json.  [{base}]")
    if status == 429:
        return (f"429 rate limited / out of quota for deployment "
                f"'{prov.deployment}'. Raise the capacity or slow the run.  [{base}]")
    return base


def _prompt_key(user_text: str) -> str:
    """First line of the user block identifies which of the 10 prompts this is."""
    for line in user_text.splitlines():
        if line.startswith("#PROMPT:"):
            return line.replace("#PROMPT:", "").strip()
    return "unknown"


def build_providers(cfg: dict[str, Any]) -> dict[str, ModelProvider]:
    """
    Factory. THIS is the swap point.

    Change a deployment name in config.json and every prompt in the lab
    runs against a different model. No other file changes.
    """
    mode = os.environ.get("DS_MODE", cfg.get("mode", "mock")).lower()
    live = mode == "live"
    cls = AzureOpenAIProvider if live else MockProvider
    out: dict[str, ModelProvider] = {}
    for name, m in cfg["models"].items():
        # In live mode the deployment name must match YOUR resource, so it is
        # read from `live_deployment` when present. The mock names stay put so
        # the offline lab keeps working unchanged.
        #
        # Resolution order: config live_deployment -> AZURE_OPENAI_DEPLOYMENT
        # -> config deployment. Config wins over env on purpose. Routing is a
        # decision that belongs in version control; the env var exists so a
        # shared resource can be repointed without editing tracked config, not
        # so it can be overridden quietly.
        deployment = (m.get("live_deployment")
                      or resolve_default_deployment()
                      or m["deployment"]) if live else m["deployment"]
        out[name] = cls(name, deployment, {**cfg, **m})
    return out
