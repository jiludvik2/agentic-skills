"""A god-ish class whose methods touch disjoint attributes -> low cohesion."""


class GrabBag:
    def __init__(self):
        self.alpha = 1
        self.beta = 2
        self.gamma = 3
        self.delta = 4

    def only_alpha(self):
        return self.alpha

    def only_beta(self):
        return self.beta

    def unrelated(self):
        return 42

    def also_unrelated(self, x):
        return x * 2
