import os
import unittest
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

class TestInclude(unittest.TestCase):
    p1 = test_folder / 'static-1.yaml'
    p2 = test_folder / 'static-2.json'
    p3 = test_folder / 'static-3.py'
    p4 = test_folder / 'static-4.py'

    def test_include(self):
        oa.configure(self.p1, include=(self.p2,))

    def test_collision(self):
        try:
            oa.configure(self.p1, include=(self.p3,))
            raise AssertionError('should have failed due to collision')
        except oa.exceptions.VariableCollisionError:
            pass

    def test_collision_between_included(self):
        try:
            oa.configure(self.p1, include=(self.p2, self.p4))
            raise AssertionError('should have failed due to collision')
        except oa.exceptions.VariableCollisionError:
            pass
