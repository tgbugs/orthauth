import unittest
import orthauth as oa
from .common import test_folder


class TestDec(unittest.TestCase):
    def setUp(self):
        sc = test_folder / 'auth-config-1.yaml'
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

    def test_after_init(self):
        @self.auth.tangential('api_key', 'test-after-init', atInit='after')
        class Test:
            def __init__(self):
                self.api_key = 'YOU FELL FOR IT FOOL'

        assert not hasattr(Test, 'api_key')
        tv = 'after-init'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_after_init_adt(self):
        dec = self.auth.tangential('api_key', 'test-after-init')
        @dec(atInit='after')
        class Test:
            def __init__(self):
                self.api_key = 'YOU FELL FOR IT FOOL'

        assert not hasattr(Test, 'api_key')
        tv = 'after-init'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_after_init_adt_should_fail(self):
        dec = self.auth.tangential('api_key', 'test-after-init')
        @dec(atInit=True)
        class Test:
            def __init__(self):
                self.api_key = 'YOU FELL FOR IT FOOL'

        assert not hasattr(Test, 'api_key')
        tv = 'after-init'
        test = Test()
        assert test.api_key == tv, [d for d in test.__dict__ if not d.startswith('__')]

    def test_after_init_adt_unset_fail(self):
        dec = self.auth.tangential('api_key', 'test-after-init', atInit=True)
        @dec(atInit=False)
        class Test:
            def __init__(self):
                self.api_key = 'YOU FELL FOR IT FOOL'

        tv = 'after-init'
        test = Test()
        assert test.api_key != tv, 'should have failed due to instance setting its own api_key'

    def test_after_init_adt_unset(self):
        dec = self.auth.tangential('api_key', 'test-after-init', atInit=True)
        @dec(atInit=False)
        class Test:
            pass

        tv = 'after-init'
        assert Test.api_key == tv
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

    def test_tangential_init_after(self):
        @self.auth.tangential_init('api_key', 'test-after-init', after=True)
        class Test:
            def __init__(self):
                self.api_key = 'YOU FELL FOR IT FOOL'

        assert not hasattr(Test, 'api_key')
        tv = 'after-init'
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

        assert test.v1 == 'a auth-config value', [d for d in test.__dict__ if not d.startswith('__')]
        assert test.v2 == 'a user value', [d for d in test.__dict__ if not d.startswith('__')]
        assert test.api_key == 'tiapi'
