from typing import Any

from code_review.adapters.bandit import BanditAdapter
from code_review.adapters.cohesion_ import CohesionAdapter
from code_review.adapters.depcruiser import DependencyCruiserAdapter
from code_review.adapters.eslint import EslintAdapter
from code_review.adapters.gitleaks import GitleaksAdapter
from code_review.adapters.jscpd import JscpdAdapter
from code_review.adapters.knip import KnipAdapter
from code_review.adapters.pydeps import PydepsAdapter
from code_review.adapters.radon import RadonAdapter
from code_review.adapters.semgrep import SemgrepAdapter
from code_review.adapters.trivy import TrivyAdapter
from code_review.adapters.vulture import VultureAdapter

# NB: typed `type[Any]` not `type[Analyzer]` — mypy rejects `type[Protocol]` as a
# value that gets instantiated (Protocols are not directly instantiable). Adapters
# still conform structurally to the Analyzer Protocol; conformance is checked by the
# per-adapter `isinstance(..., Analyzer)` tests, not at the registry type.
REGISTRY: dict[str, type[Any]] = {
    "bandit": BanditAdapter,
    "cohesion": CohesionAdapter,
    "depcruiser": DependencyCruiserAdapter,
    "eslint": EslintAdapter,
    "gitleaks": GitleaksAdapter,
    "jscpd": JscpdAdapter,
    "knip": KnipAdapter,
    "pydeps": PydepsAdapter,
    "radon": RadonAdapter,
    "semgrep": SemgrepAdapter,
    "trivy": TrivyAdapter,
    "vulture": VultureAdapter,
}
