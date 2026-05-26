def classify(x: int) -> str:
    """Intentionally high cyclomatic complexity (CC=10) for test fixture."""
    if x == 1:
        return "one"
    elif x == 2:
        return "two"
    elif x == 3:
        return "three"
    elif x == 4:
        return "four"
    elif x == 5:
        return "five"
    elif x == 6:
        return "six"
    elif x == 7:
        return "seven"
    elif x == 8:
        return "eight"
    elif x == 9:
        return "nine"
    else:
        return "other"
