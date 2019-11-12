import pathlib
import orthauth as oa

oa.utils.log.setLevel('DEBUG')

test_folder = pathlib.Path(__file__).parent / 'configs'
(test_folder / 'secrets-test-1.yaml').chmod(0o0600)
