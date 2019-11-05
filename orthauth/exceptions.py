

class OrthauthError(Exception):
    """ base class for orthauth errors """


class SecretAsKeyError(OrthauthError):
    """ Using a secret as a key in the path to another secret
        is a recipe for secrets getting committed to code. """


class UnsupportedConfigLangError(OrthauthError):
    """ Using a secret as a key in the path to another secret
        is a recipe for secrets getting committed to code. """
