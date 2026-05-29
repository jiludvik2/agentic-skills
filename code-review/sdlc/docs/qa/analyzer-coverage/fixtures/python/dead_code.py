"""Planted dead code for vulture."""
import os  # unused import

USED = 1


def used_function():
    return USED


def _unused_function():  # never called
    leftover = 42  # unused local
    return 1


class UnusedClass:  # never instantiated
    pass
