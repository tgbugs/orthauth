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
        @self.auth.tangential('api_key', 'full-complexity-example')
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


class TestDec(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_asProperty(self):
        @self.auth.tangential('api_key', 'test-as-property', asProperty=True)
        class Test:
            pass

        tv = 'apapi'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_asProperty_at_decoration_time(self):
        dec = self.auth.tangential('api_key', 'test-as-property')
        @dec(asProperty=True)
        class Test:
            pass

        tv = 'apapi'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_atInit(self):
        @self.auth.tangential('api_key', 'test-at-init', atInit=True)
        class Test:
            pass

        assert not hasattr(Test, 'api_key')
        tv = 'atapi'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_aInit_at_decoration_time(self):
        dec = self.auth.tangential('api_key', 'test-at-init')
        @dec(atInit=True)
        class Test:
            pass

        assert not hasattr(Test, 'api_key')
        tv = 'atapi'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_tangential_init(self):
        @self.auth.tangential_init('api_key', 'test-tang-init')
        class Test:
            pass

        assert not hasattr(Test, 'api_key')
        tv = 'tiapi'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_multi(self):
        @self.auth.tangential('v1', 'test-value-1', atInit=True)
        @self.auth.tangential('v2', 'test-value-2', asProperty=True)
        @self.auth.tangential_init('api_key', 'test-tang-init')
        class Test:
            pass

        test = Test()

        assert not hasattr(Test, 'v1')
        assert hasattr(Test, 'v2')
        assert Test.v2, [d for d in dir(Test) if not d.startswith('__')]
        assert not hasattr(Test, 'api_key')

        assert test.v1 == 'a static value', [d for d in test.__dict__ if not d.startswith('__')]
        assert test.v2 == 'a dynamic value', [d for d in test.__dict__ if not d.startswith('__')]
        assert test.api_key == 'tiapi'
