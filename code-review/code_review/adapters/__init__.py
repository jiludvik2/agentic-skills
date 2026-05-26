from typing import Any

from code_review.adapters.radon import RadonAdapter
from code_review.adapters.semgrep import SemgrepAdapter
from code_review.contracts import Analyzer

REGISTRY: dict[str, type[Any]] = {
    "semgrep": SemgrepAdapter,
    "radon": RadonAdapter,
}
