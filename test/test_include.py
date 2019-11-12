import shutil
import unittest
import orthauth as oa
from .common import test_folder


class TestAltConfig(unittest.TestCase):
    single = test_folder / 'static-1.yaml'
    top = test_folder / 'static-5.yaml'
    top_rename = test_folder / 'static-6.yaml'
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
    p1 = test_folder / 'static-1.yaml'
    p2 = test_folder / 'static-2.json'
    p3 = test_folder / 'static-3.py'
    p4 = test_folder / 'static-4.py'

    def tearDown(self):
        for p in (self.p2, self.p3, self.p4):
            a = oa.configure(p)
            dcp = a.dynamic_config._path
            if dcp.parent != p.parent:
                shutil.rmtree(p.parent / dcp.relative_to(p.parent).parts[0])
            else:
                dcp.unlink()

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
        test = auth.get('static-2-test-value')
        assert tv == test

    def test_get_included_user(self):
        tv = 'super duper'
        auth = oa.configure(self.p1, include=(self.p2,))
        s = auth._include[0]
        dc = s.dynamic_config
        blob = dc.load_type()
        blob['auth-variables']['static-2-test-value'] = tv
        dc.dump(blob)
        test = auth.get('static-2-test-value')
        assert tv == test
