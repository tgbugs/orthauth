import pickle
import unittest
from orthauth.utils import branches, parse_paths, QuietDict, QuietTuple
from orthauth import exceptions as exc

tree = {
    1: {4: {5: {6: None}}},
    2: {7: None,
        8: None},
    3: None,
}


class TestBranches(unittest.TestCase):
    def test_branches(self):
        out = list(branches(tree))
        assert out == [
            [1, 4, 5, 6],
            [2, 7],
            [2, 8],
            [3],
        ]


paths = [
    'hello OK is a path',
    ['so', 'is', 'this'],
    [1, 2, 3],
    ['a', 1],
]


class TestParseAndExandPaths(unittest.TestCase):
    def test_parse(self):
        l = list(parse_paths(paths))
        assert l[0] == ['hello', 'OK', 'is', 'a', 'path']
        assert l[3] == ['a', '1']


class TestQuiet(unittest.TestCase):
    def test_quiet_dict(self):
        ref = {'oh': 'nose', 'her': 'nanomachines',}
        qd = QuietDict({'oh': 'nose',
                        'her': 'nanomachines',})

        f_r = (
            (str, lambda r: r == '{secure}'),
            (repr, lambda r: r == '{secure}'),
            ((lambda i: getattr(i, 'pop')('oh')), lambda r: r == None and qd == ref),
            ((lambda i: getattr(i, 'values')()), lambda r: r == QuietTuple(ref.values())),
            ((lambda i: getattr(i, 'popitem')('her')), lambda r: r == None and qd == ref),
            ((lambda i: getattr(i, 'update')({'weo': 'weo'})), lambda r: r == None and qd == ref),
            (pickle.dumps, lambda r: pickle.loads(r) == {}),
        )
        for f, r in f_r:
            assert r(f(qd))

    def test_quiet_tuple(self):
        qt = QuietTuple((1, 2, 3, 4))

        f_r = (
            (str, lambda r: r == '[secure]'),
            (repr, lambda r: r == '[secure]'),
            (pickle.dumps, lambda r: pickle.loads(r) == tuple()),
        )
        for f, r in f_r:
            assert r(f(qt))

