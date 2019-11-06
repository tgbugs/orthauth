import os
import unittest
import pytest
import orthauth as oa
from .common import test_folder


class TestSimple(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_dynamic(self):
        print(self.auth)
        assert self.auth.dynamic_config._path == self.auth.dynamic_config_path, 'big oops'

    def test_load(self):
        @self.auth.tangential_auth('api_key', 'full-complexity-example')
        class Test:
            pass

        assert Test.api_key, [d for d in dir(Test) if not d.startswith('__')]

    def test_path_list_variant(self):
        assert self.auth.get('paths-as-list-example') == 'lol'

    def test_path_strings(self):
        assert self.auth.get('paths-example') == 'yay!'

    def test_implicit_env(self):
        assert self.auth.get('env-example') == os.environ.get('USER', None)

    def test_default(self):
        assert self.auth.get('default-example') == '42'
