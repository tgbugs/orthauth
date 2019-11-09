import os
import unittest
import yaml
import orthauth as oa
from .common import test_folder


class TestAuthConfig(unittest.TestCase):
    def test_auth_config_in_binary_blob(self):
        auth = oa.configure_relative('auth-config.py')
        blob = auth.load_type()
        assert blob == {'config-search-paths': ['../test/dynamic-1.yaml'],
                        'auth-variables': {'hrm': 'derp'}}


class TestConfigure(unittest.TestCase):
    def setUp(self):
        with open(test_folder / 'static-1.yaml', 'rt') as f:
            self.tv = yaml.safe_load(f)

    def test_configure(self):
        auth = oa.configure(test_folder / 'static-1.yaml')
        test = auth.load_type()
        assert test == self.tv

    def test_configure_relative(self):
        auth = oa.configure_relative('static-1.yaml')
        test = auth.load_type()
        assert test == self.tv


class TestSimple(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_dynamic(self):
        print(self.auth)
        assert self.auth.dynamic_config._path == self.auth.dynamic_config_path, 'big oops'

    def test_tangential(self):
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

    def test_multi_path_1(self):
        assert self.auth.get_path('test-multi-path-1') == self.auth._path

    def test_multi_path_2(self):
        assert self.auth.get_path('test-multi-path-2') == self.auth.dynamic_config._path

    def test_multi_path_3(self):
        assert self.auth.get_path('test-multi-path-3') == self.auth.dynamic_config._path


class TestMakeUserConfig(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_exists(self):
        try:
            self.auth.write_user_config()
            raise AssertionError('should not have written')
        except oa.exceptions.ConfigExistsError:
            pass

    def test_make_dynamic(self):
        output = self.auth._make_dynamic()
        assert output['auth-variables'].keys() == self.auth.get_blob('auth-variables').keys(), 'hrm'

    def _roundtrip(self, format):
        ser = self.auth._serialize_user_config(format=format)
        reloaded = self.auth._load_string(ser, format)
        test = self.auth._make_dynamic()
        assert reloaded == test, 'roundtrip failed for {format}'

    def test_serialize_json(self):
        self._roundtrip('json')

    def test_serialize_py(self):
        self._roundtrip('py')

    def test_serialize_yaml(self):
        self._roundtrip('yaml')
