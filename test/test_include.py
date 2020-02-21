import os
import shutil
import unittest
import pytest
import orthauth as oa
from .common import test_folder


class TestAltConfig(unittest.TestCase):
    single = test_folder / 'auth-config-1.yaml'
    top = test_folder / 'auth-config-5.yaml'
    top_rename = test_folder / 'auth-config-6.yaml'
    def test_single(self):
        auth = oa.configure(self.single)
        tv = 'alt config single value'
        test = auth.get('test-alt-config-single')
        assert test == tv
    def test_single_rename(self):
        auth = oa.configure(self.single)
        tv = 'alt config single rename value'
        test = auth.get('test-alt-config-single-rename')
        assert test == tv
    def test_top(self):
        auth = oa.configure(self.top)
        tv = 'alt config top value'
        test = auth.get('test-top-level-alt-config')
        assert test == tv
    def test_top_rename(self):
        auth = oa.configure(self.top_rename)
        tv = 'alt config top rename value'
        test = auth.get('name-that-would-collide-or-something')
        assert test == tv


class TestInclude(unittest.TestCase):
    p1 = test_folder / 'auth-config-1.yaml'
    p2 = test_folder / 'auth-config-2.json'
    p3 = test_folder / 'auth-config-3.py'
    p4 = test_folder / 'auth-config-4.py'
    p5 = test_folder / 'one' / 'auth-config-10.yaml'
    p6 = test_folder / 'two/three' / 'auth-config-11.yaml'

    def tearDown(self):
        for p in (self.p2, self.p3, self.p4):
            a = oa.configure(p)
            ucp = a.user_config._path
            if ucp.parent != p.parent:
                shutil.rmtree(p.parent / ucp.relative_to(p.parent).parts[0])
            else:
                ucp.unlink()

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

    def test_get_included(self):
        auth = oa.configure(self.p1, include=(self.p2,))
        tv = 'ok'
        test = auth.get('auth-config-2-test-value')
        assert tv == test

    def test_get_included_user(self):
        tv = 'super duper'
        auth = oa.configure(self.p1, include=(self.p2,))
        s = auth._include[0]
        uc = s.user_config
        blob = uc.load()
        blob['auth-variables']['auth-config-2-test-value'] = tv
        uc.dump(blob)
        test = auth.get('auth-config-2-test-value')
        assert tv == test

    def test_included_relative_path(self):
        p5c = oa.configure(self.p5)
        p6c = oa.configure(self.p6, include=(self.p5,))

        test_av = 'test-include-relative-path'

        value_p5 = p5c.get_path(test_av)
        value_p6 = p6c.get_path(test_av)
        assert value_p5 == value_p6

    def test_included_relative_path_default(self):
        p5c = oa.configure(self.p5)
        p6c = oa.configure(self.p6, include=(self.p5,))
        test_av = 'test-include-relative-path-default'

        value_p5 = p5c.get_path(test_av)
        value_p6 = p6c.get_path(test_av)
        assert value_p5 == value_p6

    def test_included_relative_path_envars(self):
        p5c = oa.configure(self.p5)
        p6c = oa.configure(self.p6, include=(self.p5,))
        test_av = 'test-include-relative-path-envars'

        value_p5 = p5c.get_path(test_av)
        value_p6 = p6c.get_path(test_av)
        assert value_p5 == value_p6
