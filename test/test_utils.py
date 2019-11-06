import unittest
from orthauth.utils import branches, parse_and_expand_paths
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


variables = {
    'this': 'OK',
}
paths = [
    'hello {this} is a path',
    ['so', 'is', 'this'],
    [1, 2, 3],
    ['a', 1],
]

bad_paths = [
    'this {var} does not exist'
]


class TestParseAndExandPaths(unittest.TestCase):
    def test_parse(self):
        l = list(parse_and_expand_paths(paths, variables))
        assert l[0] == ['hello', 'OK', 'is', 'a', 'path']
        assert l[3] == ['a', '1']

    def test_parse_fail(self):
        try:
            list(parse_and_expand_paths(bad_paths, variables))
            raise AssertionError('should fail')
        except exc.VariableNotDefinedError:
                pass
