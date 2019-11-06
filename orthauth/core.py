import os
import ast
import stat
import pathlib
from . import exceptions as exc
from .utils import branches, getenv, parse_and_expand_paths
from .utils import log, logd
from .utils import QuietDict

try:
    import yaml  # FIXME DANGERZONE :/
except ImportError as e:
    pass


def configure(auth_config_path):
    """ oa.configure(__file__) """
    return AuthConfig(auth_config_path)

class ConfigBase:
    def __new__(cls, path):
        if isinstance(path, str):
            path = pathlib.Path(path)

        self = super().__new__(cls)
        # get the type of path and set from_type
        if path.suffix == '.yaml':
            self._from_type = self._from_yaml
        elif path.suffix == '.py':
            self._from_type = self._from_python
        else:
            raise exc.UnsupportedConfigLangError(path.suffix)

        self._path = path
        return self

    def from_type(self, *names):
        return self._from_type(*names)

    def _from_python(self, *names):
        # NOTE that a config written in python CANNOT
        # be imported and should just be a literal dict
        if not names:
            raise TypeError('names is a required argument')

        with open(self._path, 'rt') as f:
            dict_literal = f.read()

        current = ast.literal_eval(dict_literal)

        for name in names:
            current = current[name]

        if fail and isinstance(current, dict):
            raise ValueError(f'Your config path is incomplete.')

        return current


    def _from_yaml(self, *names, fail=False):
        if not names:
            raise TypeError('names is a required argument')

        with open(self._path, 'rt') as f:
            current = yaml.safe_load(f)

        for name in names:
            current = current[name]

        if fail and isinstance(current, dict):
            raise ValueError(f'Your config path is incomplete.')

        return current


class AuthConfig(ConfigBase):  # FIXME this is more a schema?
    """ Object representation of a static configuration file
    that lives in a repository and that changes only when some
    change needs to be made to a decorator in the code base that
    needs authenticated access.
    
    This is the primary api entry point for orthauth.
    """

    def __new__(cls, path):
        self = super().__new__(cls, path)
        self.dynamic_config = UserConfig(self)
        return self

    def _pathit(self, path_string):
        path = pathlib.Path(path_string)
        if not path.is_absolute():
            path = self._path.parent / path

        # TODO expanduser
        return path

    @property
    def dynamic_config_path(self):
        search = [self._pathit(path_string) for path_string in
                  self.from_type('config-search-paths')]
        for path in search:
            if path.exists():
                return path

        raise FileNotFoundError(f'{search}')

    def from_type(self, *names):
        blob = self._from_type(*names)
        if blob is None:
            blob = self.dynamic_config.from_type(*names)

        if blob is None:
            raise KeyError(f'{names}')

        return blob

    def tangential_auth(self, inject_value, with_name, when=True):
        """ class decorator
            the tangential auth decorator makes a name available to
            all instances of a class from class creation time, this
            this is not fully orthogonal, but makes it easier to
            separate the logic of an API from the logic of its auth """

        def cdecorator(cls):
            setattr(cls, inject_value, self.get(with_name))
            return cls

        return cdecorator

    @property
    def secrets(self):
        return self.dynamic_config.secrets

    def _get(self, paths):
        secrets = self.secrets
        errors = []
        for names in paths:
            auth_store = self.dynamic_config.path_source(*names)  # FIXME perf issue incoming
            try:
                return auth_store(*names)
            except KeyError as e:
                errors.append(e)
                logd.error(f'broken path {names}')
                if auth_store != secrets:
                    try:
                        return secrets(*names)
                    except KeyError as e:
                        errors.append(e)

        if errors:
            raise KeyError(f'{[e.args[0] for e in errors]}') from errors[-1]

    def __call__(self, cls_or_function):
        raise NotImplementedError

    def _check(self):
        """ make sure restrictions on config structure are satisfied """
        variables

    def get(self, variable_name):
        """ look up the value of a variable name from auth store or config """
        variable_config = self.from_type('auth-variables', variable_name)
        shading = []
        shaded = []
        # env
        for evkey in ('environment-variables', 'env-vars'):
            if evkey in variable_config:
                ev = variable_config[evkey]
                if isinstance(ev, str):
                    shading += ev.split(' ')
                else:
                    if 'shading' in ev:
                        shading += ev['shading'].split(' ')

                    if 'shaded' in ev:
                        shaded += ev['shaded'].split(' ')

        raw_paths = []
        # paths
        if 'paths' in variable_config:
            raw_paths += variable_config['paths']

        if 'paths-nested' in variable_config:
            raw_paths += list(branches(variable_config['paths-nested']))

        dynamic_variables = self.dynamic_config.variables
        try:
            paths = list(parse_and_expand_paths(raw_paths, dynamic_variables))
        except exc.VariableNotDefinedError as e:
            logd.error(f'variable missing in {self.dynamic_config_path}')
            raise e  # TODO message about where missing from

        for f, v in zip((getenv, self._get, getenv), (shading, paths, shaded)):
            if v:
                SECRET = f(v)
                if SECRET is not None:
                    return SECRET


class UserConfig(ConfigBase):
    """ Same structure as secrets, but all information
    is identifying, not authenticating

    There is a strong possibility that this will only be a single
    level without any trees to simplify the interaction between
    the Static and Dynamic configs

    WARNING: if you use this to set authentication endpoints
    then make sure a malicious party cannot change the endpoint
    to steal credentials that you will be sending to that endpoint
    """

    def __new__(cls, static_config):
        path = static_config.dynamic_config_path
        self = super().__new__(cls, path)
        self.static_config = static_config
        return self

    def _auth_store(self, type_):
        try:
            return {
                'secrets': self._secrets,
                'authinfo': self._authinfo,
                'mypass': self._mypass,
            }[type_]
        except KeyError as e:
            raise exc.UnknownAuthStoreType(type_)

    def _authinfo(self, blob):
        return Authinfo(self._blob_path(blob))

    def _secrets(self, blob):
        return Secrets(self._blob_path(blob))

    def _mypass(self, blob):
        return Secrets(self._blob_path(blob))

    def _blob_path(self, blob):
        path = pathlib.Path(blob['path'])
        if path.parts[0] == ('~'):
            path = path.expanduser()

        if not path.is_absolute():
            path = self._path.parent / path

        return path


    @property
    def secrets(self):
        """ default failover for paths without explicit management """
        return self._secrets(self.from_type('auth-stores', 'secrets'))

    @property
    def variables(self):
        return self.from_type('variables')

    @property
    def _path_sources(self):
        # FIXME from type reads twice, should only read once
        variables = self.variables
        path_data = self.from_type('path-sources')
        store_data = self.from_type('auth-stores')
        out = {}
        for raw_path, type_ in path_data.items():
            try:
                names = tuple(next(parse_and_expand_paths([raw_path], variables)))
            except exc.VariableNotDefinedError as e:
                logd.error(f'variable missing in {self._path}')
                raise e  # TODO message about where missing from

            blob = store_data[type_]  # key error here is ok and expected but need good messaging
            auth_store = self._auth_store(type_)(blob)
            out[names] = auth_store

        return out

    def path_source(self, *names):
        sources = self._path_sources
        search = names
        while search:
            if search in sources:
                auth_store = sources[tuple(names)]
                return auth_store
            search = search[:-1]

        else:
            return self.secrets


class Authinfo:
    def __init__(self, path):
        if isinstance(path, str):
            path = pathlib.Path(path)

        self._path = path

    def __call__(self, *names):
        raise NotImplementedError('TODO')


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
