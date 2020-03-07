import json
import yaml
import pprint
import unittest
import orthauth as oa
from orthauth import exceptions as exc
from .common import test_folder


class TestFormats(unittest.TestCase):
    def _config(self, name):
        path = test_folder / name
        return oa.AuthConfig(path)

    def _do_test(self, auth):
        SECRET = auth.get('full-complexity-example')
        assert SECRET == 'oh-no-my-api-key-is-on-github-!', 'derp'

    def test_runtime(self):
        _source = self._config('auth-config-1.yaml')
        _ablob = _source.load()
        # FIXME user-config-path ??? more uniform with other behavior
        _ablob['config-search-paths'] = [test_folder / _ablob['config-search-paths'][0]]

        source = self._config('auth-config-1.yaml')
        ablob = source.load()
        ublob = source.user_config.load()

        with open(test_folder / 'secrets-test-1.yaml', 'rt') as f:  # please never do this irl
            sblob = yaml.safe_load(f)

        try:
            auth = oa.AuthConfig.runtimeConfig(ablob)
            assert False, 'should have failed due to non-relative-path'
        except exc.NoBasePathError:
            pass

        auth = oa.AuthConfig.runtimeConfig(_ablob)
        assert auth.get('default-example') == '42', 'deep thought required'
        auth = oa.AuthConfig.runtimeConfig(ablob, ublob)
        assert auth.get('test-after-init') == 'after-init', 'failure'
        auth = oa.AuthConfig.runtimeConfig(ablob, ublob, sblob)
        assert auth.get('oh-nose-her-api-keys') == 'DO NOT WANT', '( ͡° ͜ʖ ͡°)'

    def test_yaml(self):
        auth = self._config('auth-config-1.yaml')
        self._do_test(auth)

    def test_python(self):
        path = test_folder / 'auth-config-1.py'
        try:
            with open(test_folder / 'auth-config-1.yaml', 'rt') as f, open(path, 'wt') as o:
                d = yaml.safe_load(f)
                o.write(pprint.pformat(d))

            config = self._config(path.name)
            self._do_test(config)

        finally:
            if path.exists():
                path.unlink()

    def test_json(self):
        path = test_folder / 'auth-config-1.json'
        try:
            with open(test_folder / 'auth-config-1.yaml', 'rt') as f, open(path, 'wt') as o:
                d = yaml.safe_load(f)
                json.dump(d, o)

            config = self._config(path.name)
            self._do_test(config)

        finally:
            if path.exists():
                path.unlink()
