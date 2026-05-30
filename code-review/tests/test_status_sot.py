"""s1-t0 — ADR-0019 status taxonomy single-source-of-truth.

The status values (ok | error | timeout | unavailable) were defined three times: private
constants in ``capture.py``, the ``enum`` in ``review-bundle.v1.json``, and bare string
literals in the SARIF-path adapters. This pins one shared definition (``code_review.status``)
and asserts the published schema cannot silently drift from it.
"""

from __future__ import annotations

from code_review.capture import CaptureOutput
from code_review.review_bundle import load_bundle_schema
from code_review.status import Status

ADR0019_VALUES = {"ok", "error", "timeout", "unavailable"}


def test_status_values_are_adr0019() -> None:
    # the shared definition is exactly the ADR-0019 taxonomy — nothing more, nothing less
    assert {s.value for s in Status} == ADR0019_VALUES


def test_schema_enum_matches_status_sot() -> None:
    # the published schema's status enum and the code definition cannot drift apart
    schema = load_bundle_schema()
    enum = schema["properties"]["outputs"]["items"]["properties"]["status"]["enum"]
    assert sorted(enum) == sorted(s.value for s in Status)


def test_capture_uses_shared_status() -> None:
    # captures carry shared-enum members, guarding the private-constant removal
    assert CaptureOutput(tool="x").status in set(Status)
    assert CaptureOutput.unavailable("x", "r").status is Status.UNAVAILABLE
