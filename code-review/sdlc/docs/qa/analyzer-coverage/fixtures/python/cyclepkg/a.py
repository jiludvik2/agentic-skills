# pydeps: labelled import cycle a -> b -> a (back-edge for the precision oracle)
from cyclepkg import b

__all__ = ["b"]
