import pathlib
test_folder = pathlib.Path(__file__).parent
(test_folder / 'secrets-test-1.yaml').chmod(0o0600)
