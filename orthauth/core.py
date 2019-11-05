import yaml  # FIXME DANGERZONE :/
import stat
import pathlib


class Config:
    def __new__(cls, path):
        if isinstance(path, str):
            path = pathlib.Path(path)

        self = super().__new__(cls)
        # get the type of path and set from_type
        if path.suffix == '.yaml':
            self.from_type = self._from_yaml
        else:
            raise exc.UnsupportedConfigLangError(path.suffix)

        self.path = path
        return self

    def _from_yaml(self, *names, fail=False):
        if not names:
            raise TypeError('names is a required argument')

        with open(self.path, 'rt') as f:
            current = yaml.safe_load(f)

        for name in names:
            current = current[name]

        if fail and isinstance(current, dict):
            raise ValueError(f'Your config path is incomplete.')

        return current


class ConfigStatic(Config):  # FIXME this is more a schema?
    """ A config file that lives in a repository and that changes
    only when some change needs to be made to a decorator in the
    code base that needs authenticated access.

    name-that-goes-in-code:
      environment-variables:
        shadowing: HIGHEST_PRIORITY HIGHER_PRIORITY_API_KEY {{ insecure-dynamic-env }}
        shadowed: LOW_PRIORITY_API_KEY LOWEST_PRIORITY_API_KEY
      paths:
      insecure-paths-to-secret:
        secret:
          path:
            1:
        failover-secret:
          path:
        path:
          with:
            {{ insecure-key-from-dynamic-conifg-variable }}:
              in-the:
                path:

      insecure-paths-to-secret-path-elements:
        other-name-that-goes-in-code
    """

    def __new__(cls, path):
        self = super().__new__(cls, path)
        self.dynamic_config = ConfigDynamic(self)
        return self

    def _pathit(self, path_string):
        path = pathlib.Path(path_string)
        if not path.is_absolute():
            path = self.path.parent / path

        # TODO expanduser
        return path

    @property
    def dynamic_config_path(self):
        search = [self._pathit(path_string) for path_string in
                  self.from_type('dynamic-config-search-paths')]
        for path in search:
            if path.exists():
                return path

        raise FileNotFoundError(f'{search}')

    def tangential_auth(self, inject_value, with_name, when=True):
        """ class decorator
            the tangential auth decorator makes a name available to
            all instances of a class from class creation time, this
            this is not fully orthogonal, but makes it easier to
            separate the logic of an API from the logic of its auth """

        def cdecorator(cls):
            setattr(cls, inject_value, self(with_name))
            return cls

        return cdecorator

    def __call__(self, with_name):
        name_config = self.from_type('insecure-static-variables', with_name)
        # env
        # shadowing
        # shadowed
        # paths


class ConfigDynamic(Config):
    """ Same structure as secrets, but all information
    is identifying, not authenticating

    There is a strong possibility that this will only be a single
    level without any trees to simplify the interaction between
    the Static and Dynamic configs

    WARNING: if you use this to set authentication endpoints
    then make sure a malicious party cannot change the endpoint
    to steal credentials that you will be sending to that endpoint

    static-config-path: path/to/static/config/for-this-program
    secrets-path: path/to/secrets  # simple usage
    secrets-paths:  # complex usage
      path1:
        type: orthauth-secrets
    insecure-dynamic-variables:
      insecure-dynamic-env: HIGH_PRIORITY_API_KEY
      insecure-key-from-dynamic-conifg-variable: usernames-that-varies
      variable: also-here
    """

    def __new__(cls, static_config):
        path = static_config.dynamic_config_path
        self = super().__new__(cls, path)
        self.static_config = static_config
        return self

    @property
    def secrets_path(self):
        path = pathlib.Path(self.from_type('types', 'orthauth-secrets', 'path'))
        if not path.is_absolute():
            path = self.path.parent / path

        return path


class Secrets:
    def __init__(self, path):
        if isinstance(path, str):
            path = pathlib.Path(path)

        self._path = path
        if self.exists:
            fstat = os.stat(self._path)
            mode = oct(stat.S_IMODE(fstat.st_mode))
            if mode != '0o600' and mode != '0o700':
                raise FileNotFoundError(f'Your secrets file {self._path} '
                                        f'can be read by the whole world! {mode}')

    @property
    def filename(self):
        return self._path.as_posix()

    @property
    def exists(self):
        e = self._path.exists()
        if not e:
            raise FileNotFoundError(self._path)

        return e

    @property
    def name_id_map(self):
        # sometimes the easiest solution is just to read from disk every single time
        if self.exists:
            with open(self.filename, 'rt') as f:
                return QuietDict(yaml.safe_load(f))

    def __call__(self, *names):
        if self.exists:
            nidm = self.name_id_map
            # NOTE under these circumstances this pattern is ok because anyone
            # or anything who can call this function can access the secrets file.
            # Normally this would be an EXTREMELY DANGEROUS PATTERN. Because short
            # secrets could be exposted by brute force, but in thise case it is ok
            # because it is more important to alert the user that they have just
            # tried to use a secret as a name and that it might be in their code.
            def all_values(d):
                for v in d.values():
                    if isinstance(v, dict):
                        yield from all_values(v)
                    else:
                        yield v

            av = set(all_values(nidm))
            current = nidm
            nidm = None
            del nidm
            for name in names:
                if name in av:
                    ANGRY = '*' * len(name)
                    av = None
                    name = None
                    names = None
                    current = None
                    del av
                    del name
                    del names
                    del current
                    raise exc.SecretAsKeyError(f'WHY ARE YOU TRYING TO USE A SECRET {ANGRY} AS A NAME!?')
                else:
                    try:
                        current = current[name]
                    except KeyError as e:
                        av = None
                        name = None
                        names = None
                        current = None
                        del av
                        del name
                        del names
                        del current
                        raise e

            if isinstance(current, dict):
                raise ValueError(f'Your secret path is incomplete. Keys are {sorted(current.keys())}')

            if '-file' in name and current.startswith('~/'):  # FIXME usability hack to allow ~/ in filenames
                current = pathlib.Path(current).expanduser().as_posix()  # for consistency with current practice, keep paths as strings
            return current
