import os
import logging
from . import exceptions as exc

try:
    from sxpyr import sxpyr
except ImportError as e:
    pass


def python_to_sxpr(thing):
    pl = sxpyr.python_to_sxpr(thing)
    return pl._print(sxpyr.print_plist)


def sxpr_to_python(string):
    parse_plist = sxpyr.configure(**sxpyr.conf_plist)  # FIXME error on lack of **
    read_plist = sxpyr.conf_read(parse_plist, sxpyr.WalkPl)
    def cf(ast):
        sxpyr  # yay scoping rules
        if isinstance(ast, sxpyr.PList):
            v = [_.caste(cf) if hasattr(_, 'caste') else _
                 for _ in ast.value]  # recurse
            if v:
                return sxpyr.plist_to_dict(v)
        elif isinstance(ast, sxpyr.List):
            # XXX this isn't the ast at this point, it is the DataType layer
            # sometimes an Ast leaks through ... sigh inhomogenaity in the IR
            return [_.caste(cf) if hasattr(_, 'caste') else cf(_)
                    for _ in ast.value]
        elif isinstance(ast, sxpyr.Ast):
            return ast.value
        else:
            return ast

    def _cf(ast):
        if False and isinstance(ast, sxpyr.PList):
            return sxpyr.plist_to_dict(ast.value)
        elif isinstance(ast, sxpyr.ListAbstract):
            return [_.caste(cf) for _ in ast.collect]
        elif isinstance(ast, sxpyr.Ast):
            return ast.value
        elif isinstance(ast, str):
            return ast
        else:
            raise NotImplementedError(f'asdf {ast!r}')
            return ast

    _raw = list(read_plist(string))
    if not _raw:
        # note that nil () -> python [] so None is python convention
        # however because this is in orthauth we just raise the empty
        # config error and cut out the middleman
        raise exc.EmptyConfigError()

    raw = _raw[0]
    asdf = raw.caste(cf)
    return asdf


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


def parse_paths(raw_paths):
    for elements in raw_paths:
        if isinstance(elements, str):
            elements = elements.split(' ')

        
        path = []
        for element in elements:
            if isinstance(element, int):
                element = str(element)

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
        return (tuple, tuple())


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
        return (dict, tuple())
