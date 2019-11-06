

class OrthauthError(Exception):
    """ base class for orthauth errors """


class SecretAsKeyError(OrthauthError):
    """ Using a secret as a key in the path to another secret
        is a recipe for secrets getting committed to code. """


class UnknownAuthStoreType(OrthauthError):
    """ This type of authentication store is unknown """

class UnsupportedConfigLangError(OrthauthError):
    """ Using a secret as a key in the path to another secret
        is a recipe for secrets getting committed to code. """


class VariableNotDefinedError(OrthauthError):
    """ Variable is not know to any config file """
