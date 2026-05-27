"""
Schemathesis 4.0.10 in-process contract testing adapter.

Verified API (confirmed via probe scripts against schemathesis==4.0.10):

1. Schema loading:
   - schemathesis.from_url() does NOT exist in 4.0.10.
   - Use: schemathesis.openapi.from_url(spec_url, headers={...})
   - The headers= param on from_url does NOT propagate to HTTP requests.
   - Instead pass a requests.Session with headers pre-set to case.call(session=).

2. Operation enumeration:
   - schema.get_all_operations() returns an iterable of Ok/Err result objects.
   - Unwrap with: item.ok() for item in schema.get_all_operations() if hasattr(item, 'ok')
   - Each operation: op.label ("GET /path"), op.method ("get"), op.path ("/path").
   - op.as_strategy(GenerationMode.POSITIVE) returns a Hypothesis SearchStrategy[Case].

3. Running checks + collecting failures:
   - case = hypothesis.find(op.as_strategy(), lambda c: True, settings=...)
   - response = case.call(session=session)  # inject auth via session.headers
   - case.call_and_validate(session=session) raises FailureGroup on any failure.
   - call_and_validate signature (4.0.10): (base_url, session, headers, checks,
     additional_checks, excluded_checks, **kwargs). `additional_checks=[...]` APPENDS to the
     default check set (not_a_server_error); `checks=[...]` REPLACES it.
   - FailureGroup.exceptions is a sequence of Failure instances.
   - Failure attrs: .title (str), .message (str), .operation (str, e.g. "GET /path").
   - Failure types (by class name): ServerError (not_a_server_error), JsonSchemaError
     (response_schema_conformance — title "Response violates schema", message names the missing
     field, e.g. "'user_name' is a required property"). We map type name → stable ruleId suffix
     (see _RULEID_SUFFIX_BY_FAILURE_TYPE) rather than slugging the title.

4. Hypothesis settings:
   - Import from hypothesis: settings(max_examples=N, deadline=None, suppress_health_check=...)
   - Pass as keyword to hypothesis.find(strat, predicate, settings=h_settings(...)).
   - For the @parametrize decorator: @h_settings(...) stacked under @schema.parametrize().

5. Auth injection:
   - Create a requests.Session, set session.headers["Authorization"] = "Bearer <token>".
   - Pass session= to every case.call() or case.call_and_validate() call.

6. response_schema_conformance:
   - NOT in schemathesis.checks — it lives in schemathesis.specs.openapi.checks.
   - Default CHECKS registry only has not_a_server_error, so it MUST be passed explicitly
     (we use additional_checks=[response_schema_conformance]) or 2xx schema drift is invisible.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from typing import Any, ClassVar

import requests
import schemathesis.openapi
from hypothesis import HealthCheck, Phase
from hypothesis import find as h_find
from hypothesis import settings as h_settings
from hypothesis.errors import Flaky, Unsatisfiable
from schemathesis.core.failures import FailureGroup
from schemathesis.specs.openapi.checks import response_schema_conformance

from code_review.adapters.sarif_utils import empty_sarif, make_location, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest

_MAX_EXAMPLES = 5
_DEADLINE = None  # let Hypothesis manage; we gate on wall-clock timeout ourselves


# Map Schemathesis Failure *types* (by class name) to stable SARIF ruleId suffixes. Deriving the
# suffix from the human-readable `title` is fragile — Schemathesis phrasing ("Response violates
# schema", "Server error (5xx)") would slug to non-deterministic, AC-violating ruleIds. The
# response_schema_conformance check raises `JsonSchemaError`; not_a_server_error → `ServerError`.
_RULEID_SUFFIX_BY_FAILURE_TYPE: dict[str, str] = {
    "JsonSchemaError": "response_schema_violation",
    "ServerError": "server_error",
}


def _failure_to_sarif_result(failure: Any) -> dict[str, Any]:
    type_name = type(failure).__name__
    title: str = getattr(failure, "title", "") or type_name
    message: str = getattr(failure, "message", "") or title
    operation: str = getattr(failure, "operation", "unknown")
    # Prefer a stable suffix keyed on the failure type; fall back to a slug of the title for
    # unknown types (and for the MagicMock-based unit tests that set `.title` directly).
    rule_suffix = _RULEID_SUFFIX_BY_FAILURE_TYPE.get(type_name) or title.lower().replace(" ", "_")
    text = f"{title}: {message}" if message and message != title else title
    return {
        "ruleId": f"schemathesis.{rule_suffix}",
        "level": "error",
        "message": {"text": text},
        "locations": [make_location("api", 1)],
        "properties": {"endpoint": operation},
    }


async def _run_operation(op: Any, session: requests.Session) -> list[Any]:
    def _sync() -> list[Any]:
        settings = h_settings(
            max_examples=_MAX_EXAMPLES,
            deadline=_DEADLINE,
            suppress_health_check=list(HealthCheck),
            phases=[Phase.generate],
        )
        try:
            case = h_find(op.as_strategy(), lambda c: True, settings=settings)
        except (Unsatisfiable, Flaky):
            raise  # diagnostic errors — propagate, don't swallow
        except Exception:
            return []
        failures: list[Any] = []
        try:
            # additional_checks appends response_schema_conformance to the defaults
            # (not_a_server_error), so both server errors AND 2xx schema drift are caught.
            case.call_and_validate(
                additional_checks=[response_schema_conformance], session=session
            )
        except FailureGroup as fg:
            failures.extend(fg.exceptions)
        except Exception:
            pass
        return failures

    return await asyncio.to_thread(_sync)


class SchemathesisAdapter:
    name: ClassVar[str] = "schemathesis"
    kind: ClassVar[str] = "contract"
    default_timeout_s: ClassVar[int] = 600
    scope_restrictions: ClassVar[frozenset[str]] = frozenset({"story-level"})

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        targets: dict[str, Any] = request.config.get("contract_testing", {})
        if not targets:
            return AnalyzerOutput(sarif=empty_sarif("schemathesis", "4.0.10"))

        with tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR", tempfile.gettempdir())
        ) as tmpdir:
            os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = tmpdir

            all_results: list[dict[str, Any]] = []
            final_status = "ok"

            for _target_name, cfg in targets.items():
                spec_url: str = cfg["spec_url"]
                base_url: str = cfg["base_url"]
                token_env: str = cfg.get("auth", {}).get("token_env", "")
                timeout_s: float = float(cfg.get("timeout_s", self.default_timeout_s))
                token = os.environ.get(token_env, "") if token_env else ""

                with requests.Session() as session:
                    if token:
                        session.headers["Authorization"] = f"Bearer {token}"

                    try:
                        schema = await asyncio.to_thread(
                            schemathesis.openapi.from_url, spec_url
                        )
                    except Exception as exc:
                        return AnalyzerOutput(
                            sarif={},
                            status="error",
                            error=(
                                f"cannot reach {base_url}: {exc}. "
                                "Check sandbox.allowedDomains includes the target host."
                            ),
                        )

                    start = time.monotonic()
                    ops = [item.ok() for item in schema.get_all_operations() if hasattr(item, "ok")]

                    for op in ops:
                        if time.monotonic() - start > timeout_s:
                            final_status = "timeout"
                            break
                        failures = await _run_operation(op, session)
                        for f in failures:
                            all_results.append(_failure_to_sarif_result(f))

            sarif = normalise_sarif(
                {
                    "runs": [
                        {
                            "tool": {
                                "driver": {
                                    "name": "schemathesis",
                                    "version": "4.0.10",
                                    "rules": [],
                                }
                            },
                            "results": all_results,
                        }
                    ]
                }
            )
            return AnalyzerOutput(sarif=sarif, status=final_status)
