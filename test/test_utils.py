import unittest
from orthauth.utils import branches, parse_paths
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
