import pathlib
import orthauth as oa

oa.utils.log.setLevel('DEBUG')

test_folder = pathlib.Path(__file__).parent / 'configs'

s1 = test_folder / 'secrets-test-1.yaml'
s1.chmod(0o0600)

s2 = (test_folder / '../secrets/secrets-2.yaml').resolve()
s2.chmod(0o0600)

se = (test_folder / 'secrets-empty.yaml').resolve()
se.chmod(0o0600)
