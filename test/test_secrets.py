import unittest
import orthauth as oa
from orthauth import exceptions as exc
from .common import test_folder


class TestSecrets(unittest.TestCase):

    def setUp(self):
        auth = oa.configure(test_folder / 'auth-config-1.yaml')
        self.secrets = auth.user_config.secrets  # this is secrets-test-1.yaml

    def test_ANGRY(self):
        try:
            test = self.secrets('evil-path', 'DO NOT WANT')
            assert False, 'should have failed'
        except exc.SecretAsKeyError:
            pass

    def test_dissapointed(self):
        try:
            test = self.secrets('user', 'defined', 'path')
            assert False, 'should have failed'
        except exc.SecretPathError:
            pass

    def test_ANGRY_dissapointed(self):
        try:
            test = self.secrets('really-evil-path', 'paved', 'with')
            assert False, 'should have failed'
        except exc.SecretAsKeyError:
            pass

    def test_ANGRIER_dissapointed(self):
        try:
            test = self.secrets('really-evil-path', 'paved', 'utoh')
            assert False, 'should have failed'
        except exc.SecretAsKeyError:
            pass

    def test_null(self):
        try:
            test = self.secrets('you', 'see', 'nothing')
            assert False, 'should have failed'
        except exc.SecretEmptyError:
            pass
