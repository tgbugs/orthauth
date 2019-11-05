class QuietTuple(tuple):
    """ read only doesn't print, repr, reduce etc. """
    def __add__(self, value):
        raise TypeError('NOPE')

    def __repr__(self):
        return '[secure]'

    def __str__(self):
        return '[secure]'

    def __reduce__(self):
        return (list, tuple())


class QuietDict(dict):
    """ read only doesn't print, repr, reduce etc. """
    def copy(self):
        return None

    def pop(self, key):
        return None

    def popitem(self, key):
        return None

    def update(self, value):
        return None

    def values(self):
        return QuietTuple(super().values())

    def __repr__(self):
        return '{secure}'

    def __str__(self):
        return '{secure}'

    def __reduce__(self):
        return (dict, {})



