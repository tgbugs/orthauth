import os
import pathlib
import unittest
import pytest
from orthauth import ConfigStatic

test_folder = pathlib.Path(__file__).parent

class TestSimple(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-1.yaml'
        self.cs = ConfigStatic(sc)

    def test_dynamic(self):
        print(self.cs)
        assert self.cs.dynamic_config.path == self.cs.dynamic_config_path, 'big oops'

    def test_load(self):
        @self.cs.tangential_auth('api_key', 'name-that-goes-in-code')
        class Test:
            pass

        assert Test.api_key, [d for d in dir(Test) if not d.startswith('__')]

    def test_path_list_variant(self):
        assert self.cs('other-name-that-goes-in-code') == 'lol'

    def test_path_strings(self):
        assert self.cs('paths-example') == 'OOOOOOH NOOOOOOOOO!'

    def test_implicit_env(self):
        assert self.cs('env-example') == os.environ.get('USER', None)
