class MaxLength(object):
    def __init__(self, max_length):
        self.max_length = max_length

    def __call__(self, value):
        return len(value) <= self.max_length

class MinLength(object):
    def __init__(self, min_length):
        self.min_length = min_length

    def __call__(self, value):
        return len(value) >= self.min_length
