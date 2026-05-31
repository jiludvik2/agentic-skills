# pydeps: labelled import cycle b -> a -> b (back-edge for the precision oracle)
from cyclepkg import a

__all__ = ["a"]
