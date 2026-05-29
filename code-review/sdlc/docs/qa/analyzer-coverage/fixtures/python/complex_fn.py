"""High cyclomatic-complexity function for radon (reported via metrics.per_file)."""


def tangled(a, b, c, d, e):
    total = 0
    for i in range(a):
        if i % 2 == 0:
            if b > 0:
                total += 1
            elif b < 0:
                total -= 1
            else:
                total += 2
        elif i % 3 == 0:
            if c > 0:
                total += 3
            else:
                total -= 3
        else:
            if d > 0 and e > 0:
                total += 4
            elif d < 0 or e < 0:
                total -= 4
            else:
                total += 5
    while total > 100:
        total -= 10
        if total % 7 == 0:
            break
    return total
