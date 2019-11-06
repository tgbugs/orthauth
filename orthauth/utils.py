import os
import logging
from . import exceptions as exc


def makeSimpleLogger(name, level=logging.INFO):
    # TODO use extra ...
    logger = logging.getLogger(name)
    logger.setLevel(level)
    ch = logging.StreamHandler()  # FileHander goes to disk
    fmt = ('[%(asctime)s] - %(levelname)8s - '
           '%(name)14s - '
           '%(filename)16s:%(lineno)-4d - '
           '%(message)s')
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


log = makeSimpleLogger('orthauth')
logd = log.getChild('data')


def getenv(ordered_vars):
    for var in ordered_vars:
        if var in os.environ:
            value = os.environ[var]
            if value is not None:
                return value


def branches(tree):
    for name, subtree in tree.items():
        if subtree is None:
            yield [name]
        else:
            for subbranch in branches(subtree):
                yield [name, *subbranch]


def parse_and_expand_paths(raw_paths, variables):
    for elements in raw_paths:
        if isinstance(elements, str):
            elements = elements.split(' ')

        
        path = []
        for element in elements:
            if isinstance(element, int):
                element = str(element)
            elif element.startswith('{'):
                try:
                    element = element.format(**variables)
                except KeyError as e:
                    var = element.strip('{').rstrip('}')
                    raise exc.VariableNotDefinedError(f'variable {var!r} is not defined') from e

            path.append(element)

        yield path


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



