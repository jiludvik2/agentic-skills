from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("claude-code-review")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
