import os
import sys
import pathlib
import unittest
import yaml
import orthauth as oa
from .common import test_folder, s1, s2


class TestAuthConfig(unittest.TestCase):
    def test_auth_config_in_binary_blob(self):
        auth = oa.configure_relative('auth-config.py')
        blob = auth.load_type()
        assert blob == {'config-search-paths': ['../test/configs/dynamic-1.yaml'],
                        'auth-variables': {'hrm': 'derp'}}

    def test_bad_alt_config(self):
        try:
            auth = oa.configure(test_folder / 'static-bad-alt-config.yaml')
            auth.get('test')
            raise AssertionError('should have failed')
        except oa.exceptions.BadAuthConfigFormatError:
            pass


class TestConfigure(unittest.TestCase):
    def setUp(self):
        with open(test_folder / 'static-1.yaml', 'rt') as f:
            self.tv = yaml.safe_load(f)

    def test_configure(self):
        auth = oa.configure(test_folder / 'static-1.yaml')
        test = auth.load_type()
        assert test == self.tv

    def test_configure_relative(self):
        auth = oa.configure_relative('static-0.yaml')
        test = auth.load_type()
        tv = {'config-search-paths': ['configs/dynamic-1.yaml'],
              'auth-variables': {'default-example': None}}
        assert test == tv


class TestSimple(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-1.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_null_path(self):
        assert self.auth.get('test-null-path') is None
        assert self.auth.get_path('test-null-path') is None

    def test_config_vars(self):
        g = self.auth.get('test-config-vars')
        d = self.auth.get_default('test-config-vars')
        assert g != d
        gtv = self.auth._pathit(g)
        dtv = self.auth._pathit(d)
        assert gtv != dtv

        test = self.auth.get_path('test-config-vars')
        assert test == pathlib.Path(sys.prefix, 'share/orthauth/.does-not-exist')
        assert test == gtv
        assert test != dtv

    def test_get_default(self):
        g = self.auth.get('test-config-vars')
        d = self.auth.get_default('test-config-vars')
        assert g != d
        gtv = self.auth._pathit(g)
        dtv = self.auth._pathit(d)
        assert gtv != dtv

        test = self.auth.get_path_default('test-config-vars')
        assert test == pathlib.Path.cwd() / 'share/orthauth/.does-not-exist'
        assert test != gtv
        assert test == dtv

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

    def test_env_list(self):
        tv = 'so'
        os.environ['QUITE'] = tv
        try:
            assert self.auth.get('env-list-example') == tv
        finally:
            os.environ.pop('QUITE')

    def test_expanduser(self):
        tv = pathlib.Path('~/').expanduser()
        assert self.auth.get_path('test-expanduser') == tv

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


class TestWithStores(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'static-8.yaml'
        self.auth = oa.AuthConfig(sc)

    def test_path_relative_store(self):
        tv = s2.parent / 'some-other-relative-path.ext'
        test = self.auth.get_path('rel-secrets-path')
        assert test == tv
