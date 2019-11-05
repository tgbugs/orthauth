import unittest
import pathlib
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

    @pytest.mark.skip('not ready')
    def test_load(self):
        @self.cs.tangential_auth('api_key', 'name-that-goes-in-code')
        class Test:
            pass

        assert Test.api_key, [d for d in dir(Test) if not d.startswith('__')]
