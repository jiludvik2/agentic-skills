from typing import Any

from code_review.adapters.bandit import BanditAdapter
from code_review.adapters.radon import RadonAdapter
from code_review.adapters.semgrep import SemgrepAdapter

# NB: typed `type[Any]` not `type[Analyzer]` — mypy rejects `type[Protocol]` as a
# value that gets instantiated (Protocols are not directly instantiable). Adapters
# still conform structurally to the Analyzer Protocol; conformance is checked by the
# per-adapter `isinstance(..., Analyzer)` tests, not at the registry type.
REGISTRY: dict[str, type[Any]] = {
    "bandit": BanditAdapter,
    "semgrep": SemgrepAdapter,
    "radon": RadonAdapter,
}
