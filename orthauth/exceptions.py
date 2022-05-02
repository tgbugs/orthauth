

class OrthauthError(Exception):
    """ base class for orthauth errors """


class SecretError(OrthauthError):
    """ base clasee for errors related to secrets files """


class SecretAsKeyError(SecretError):
    """ Using a secret as a key in the path to another secret
        is a recipe for secrets getting committed to code. """


class SecretPathError(SecretError):
    """ Something is wrong with a config/auth/secret path spec
        it might be too long, it might be too short, it might
        contain a secret, etc. """


class SecretEmptyError(SecretError):
    """ Having empty paths in secret files is bad practice.
        If we detect the issue at runtime we raise this error. """


class UnknownAuthStoreType(OrthauthError):
    """ This type of authentication store is unknown """


class UnsupportedConfigLangError(OrthauthError):
    """ Using a secret as a key in the path to another secret
        is a recipe for secrets getting committed to code. """


class VariableNotDefinedError(OrthauthError):
    """ Variable is not know to any config file """


class ConfigExistsError(OrthauthError):
    """ Config file already exists, so don't overwrite it """


class EmptyConfigError(OrthauthError):
    """ Config file is empty! """


class VariableCollisionError(OrthauthError):
    """ a variable is colliding between configs """


class BadAuthConfigFormatError(OrthauthError):
    """ that's some baaaaad data """


class SomethingWrongWithVariableInConfig(OrthauthError):
    """ a variable in a config is bad """


class NoBasePathError(OrthauthError):
    """ tried to resolve a path relative to None usually because
        a runtime config value was not an absolute path"""


class BadFilePermissionsError(OrthauthError):
    """ file or folder has bad/dangerous/insecure settings """


