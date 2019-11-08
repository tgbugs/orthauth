import json
import yaml
import pprint
import unittest
import orthauth as oa
from .common import test_folder


class TestFormats(unittest.TestCase):
    def _config(self, name):
        path = test_folder / name
        return oa.AuthConfig(path)

    def _do_test(self, auth):
        SECRET = auth.get('full-complexity-example')
        assert SECRET == 'oh-no-my-api-key-is-on-github-!', 'derp'

    def test_yaml(self):
        auth = self._config('static-1.yaml')
        self._do_test(auth)

    def test_python(self):
        path = test_folder / 'static-1.py'
        try:
            with open(test_folder / 'static-1.yaml', 'rt') as f, open(path, 'wt') as o:
                d = yaml.safe_load(f)
                o.write(pprint.pformat(d))

            config = self._config(path.name)
            self._do_test(config)

        finally:
            if path.exists():
                path.unlink()

    def test_json(self):
        path = test_folder / 'static-1.json'
        try:
            with open(test_folder / 'static-1.yaml', 'rt') as f, open(path, 'wt') as o:
                d = yaml.safe_load(f)
                json.dump(d, o)

            config = self._config(path.name)
            self._do_test(config)

        finally:
            if path.exists():
                path.unlink()
