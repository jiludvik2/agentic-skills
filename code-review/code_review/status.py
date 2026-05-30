"""The ADR-0019 analyzer status taxonomy — single source of truth.

One shared definition referenced by ``capture.py`` (the raw-capture rail), by
``review_bundle.py`` (the serialised contract), and asserted equal to the ``status`` enum
published in ``review-bundle.v1.json`` (see ``tests/test_status_sot.py``). A ``StrEnum`` so
members compare equal to their string value and serialise as plain strings in JSON.

ADR-0019 meaning:
- ``ok`` — the tool ran to completion on a tolerated exit code.
- ``error`` — the tool failed to run, or exited with an untolerated code.
- ``timeout`` — the tool was killed after exceeding its time budget.
- ``unavailable`` — an adapter pre-flight decided the tool is not runnable (missing
  binary/config); the tool was never invoked.
"""

from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
