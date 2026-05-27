class LowCohesionService:
    """Intentionally low-cohesion class for testing."""

    def __init__(self) -> None:
        self.x = 1
        self.y = 2

    def get_x(self) -> int:
        return self.x

    def get_y(self) -> int:
        return self.y

    def unrelated_a(self) -> str:
        return "hello"

    def unrelated_b(self) -> str:
        return "world"

    def unrelated_c(self) -> int:
        return 42
