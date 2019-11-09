import os
import ast
import sys
import json
import stat
import inspect
import pathlib
import functools
import importlib
from pprint import pformat
from . import exceptions as exc
from .utils import branches, getenv, parse_paths
from .utils import log, logd
from .utils import QuietDict

try:
    import yaml  # FIXME DANGERZONE :/
except ImportError as e:
    pass


def configure(auth_config_path, include=tuple()):
    """ hrm """
    return AuthConfig(auth_config_path, include=include)


def configure_relative(name, include=tuple()):
    """ hrm """
    stack = inspect.stack(0)
    s1 = stack[1]
    calling__file__ = s1.filename
    calling_module = inspect.getmodule(s1.frame)
    log.warning(calling_module)
    log.warning(calling_module.__name__)
    log.warning(calling_module.__file__)
    return AuthConfig._from_relative_path(calling__file__,
                                          name,
                                          include=include,
                                          calling_module=calling_module)


class ConfigBase:

    def __new__(cls, path, include=tuple()):
        if isinstance(path, str):
            path = pathlib.Path(path)

        self = super().__new__(cls)
        try:
            self._load_type = {'.json': self._load_json,
                               '.py': self._load_python,
                               '.yaml': self._load_yaml}[path.suffix]
        except KeyError as e:
            raise exc.UnsupportedConfigLangError(path.suffix) from e

        self._path = path

        if include:  # unqualified include ... in theory we could nest everything
            if isinstance(include, cls):
                include = include,

            inc = []
            avs = [self.get_blob('auth-variables')]
            for ipath in include:
                if isinstance(ipath, cls):
                    ic = ipath
                else:
                    ic = cls(ipath)

                inc.append(ic)
                iav = ic.get_blob('auth-variables')
                avs.append(iav)

            bads = set()
            for av in avs:
                others = set(k for a in avs if a != av for k in a)
                bads |= set(k for k in av if k in others) | set(k for k in others if k in av)

            if bads:
                raise exc.VariableCollisionError(f'{bads}')

            self._include = tuple(inc)

        else:
            self._include = tuple()

        return self

    def load_type(self):
        return self._load_type()

    def dump(self, config):
        """ Don't use this ... seriously """
        format = self._path.suffix.strip('.')
        string = self._dump(config, format)
        with open(self._path, 'wt') as f:
            f.write(string)

    def _dump(self, config, format):
        if format == 'json':
            return json.dumps(config, indent=2, sort_keys=True)
        elif format == 'py':
            return pformat(config)
        elif format == 'yaml':
            return yaml.dump(config, default_flow_style=False)
        else:
            raise NotImplementedError(f'serialization to {format!r} is not ready')

    def get_blob(self, *names, fail=False):
        if not names:
            raise TypeError('names is a required argument')

        current = self.load_type()

        for name in names:
            current = current[name]

        if fail and isinstance(current, dict):
            raise ValueError(f'Your config path is incomplete.')

        return current

    def _load_string(self, string, format):
        loadf = {'json': json.loads,
                 'py': ast.literal_eval,
                 'yaml': yaml.safe_load,}[format]
        return loadf(string)

    def _load_json(self):
        with open(self._path, 'rt') as f:
            return json.load(f)

    def _load_python(self):
        """ python configuraiton files should be only a single dict literal """
        if (hasattr(self, '_calling_module') and
            self._path.suffix == '.py' and
            not self._path.exists()):
            # there are certain ways of installing a python package that
            # stick an auth-config.py file in a binary blob so we need to
            # do this little dance to guess the right module name and
            # import it including files with dashes in their name
            p = pathlib.Path(self._calling_module.__file__).parent
            prt = self._path.relative_to(p)
            modpath = '.'.join([p.name, *prt.with_suffix('').as_posix().split('/')])
            module = importlib.import_module(modpath)
            source = inspect.getsource(module)
            return ast.literal_eval(source)

        with open(self._path, 'rt') as f:
            return ast.literal_eval(f.read())

    def _load_yaml(self):
        with open(self._path, 'rt') as f:
            return yaml.safe_load(f)

    @staticmethod
    def _envars(var_config):
        envars = []
        # env
        for evkey in ('environment-variables', 'env-vars'):
            if evkey in var_config:
                ev = var_config[evkey]
                if isinstance(ev, str):
                    envars += ev.split(' ')
                else:
                    if 'envars' in ev:
                        envars += ev['envars'].split(' ')

        return envars

    @staticmethod
    def _paths(var_config):
        raw_paths = []
        # paths
        if 'path' in var_config:
            raw_paths += [var_config['path']]

        if 'paths' in var_config:
            raw_paths += var_config['paths']

        if 'paths-nested' in var_config:
            raw_paths += list(branches(var_config['paths-nested']))

        try:
            paths = list(parse_paths(raw_paths))
        except exc.VariableNotDefinedError as e:
            raise e  # TODO message about where missing from

        return paths

    def _pathit(self, path_string):
        if '{:' in path_string:  # special paths  # FIXME vs startswith
            path_string = path_string.replace('{:', '{')
            path_string = path_string.format(**self._config_vars)

        path = pathlib.Path(path_string)

        if path.parts[0] == ('~'):
            path = path.expanduser()

        if not path.is_absolute():
            path = self._path.parent / path

        return path

    @property
    def _config_vars(self):
        """ currently supported config vars

            user-config-path
        """
        if os.name != 'nt':
            if sys.platform == 'darwin':
                ucp = '~/Library/Application Support'
            else:
                ucp = '~/.config'
        else:
            ucp = '~/AppData/Local'

        return {'user-config-path': ucp,}


class AuthConfig(ConfigBase):  # FIXME this is more a schema?
    """ Object representation of a static configuration file
    that lives in a repository and that changes only when some
    change needs to be made to a decorator in the code base that
    needs authenticated access.

    This is the primary api entry point for orthauth.
    """

    @classmethod
    def _from_relative_path(cls, calling__file__, name, include=tuple(), calling_module=None):
        self = super().__new__(cls, pathlib.Path(calling__file__).parent / name, include=include)
        self._calling_module = calling_module
        self.dynamic_config = UserConfig(self)
        return self

    def __new__(cls, path, include=tuple()):
        self = super().__new__(cls, path, include=include)
        self.dynamic_config = UserConfig(self)
        return self

    @property
    def dynamic_config_paths(self):
        return [self._pathit(path_string) for path_string in
                self.get_blob('config-search-paths')]

    @property
    def dynamic_config_path(self):
        dcps = self.dynamic_config_paths
        for path in dcps:
            if path.exists():
                return path

        # if no config exists automatically create the default
        dcp = dcps[0]  # you MUST have a user config path
        self.write_user_config(dcp=dcp)
        return dcp

    def load_type(self):
        if not hasattr(self, '_blob'):
            self._blob = super().load_type()

        return self._blob

    def get_blob(self, *names):
        blob = super().get_blob(*names)
        if blob is None:
            raise KeyError(f'{names}')

        return blob

    def environ(self, set_envar, from_name, when=True):
        """ in order to use orthauth with other projects that are not aware of
            its existence and that make use of environment variables orthauth
            can set the envar that the other project expects using a value from
            an orthauth managed auth store """
        raise NotImplementedError('TODO')

    def tangential_init(self, inject_value, with_name, when=True, after=False):
        """ tangential decorator that defaults to atInit since it is a common use case """
        atInit = 'after' if after else True
        return self.tangential(inject_value, with_name, when=when, atInit=atInit)

    def tangential(self, inject_value, with_name, when=True, asProperty=False, atInit=False):
        """ class decorator
            the tangential auth decorator makes a name available to
            all instances of a class from class creation time, this
            this is not fully orthogonal, but makes it easier to
            separate the logic of an API from the logic of its auth

            In some cases this can be used to overwrite an auth variable
            in a class from a project that is unaware that orthauth exists.

            atInit='after' -> bind the value after the original __init__
            instead of before, useful in cases where the value is set
            during __init__ """

        if not when:
            # FIXME not ready
            return lambda cls: cls

        if asProperty and atInit:
            raise ValueError('asProperty and atInit are mutually exclusive')

        @property
        def tangential_property(self, outer_self=self, name=with_name):
            return outer_self.get(name)

        def cdecorator(cls=None, asProperty=asProperty, atInit=atInit):
            if asProperty and atInit:
                raise ValueError('asProperty and atInit are mutually exclusive')

            if cls is None:
                if asProperty:
                    def inner_cdec(icls):
                        setattr(icls, inject_value, tangential_property)
                        return icls

                    return inner_cdec
                elif atInit:
                    if atInit == 'after':
                        def inner_cdec(icls):
                            cls__init__ = cls.__init__
                            @functools.wraps(cls__init__)
                            def __init__(inner_self, *args, **kwargs):
                                cls__init__(inner_self, *args, **kwargs)
                                setattr(inner_self, inject_value, self.get(with_name))

                            setattr(icls, '__init__', __init__)
                            return icls
                    else:  # life-without-macros
                        def inner_cdec(icls):
                            cls__init__ = cls.__init__
                            @functools.wraps(cls__init__)
                            def __init__(inner_self, *args, **kwargs):
                                setattr(inner_self, inject_value, self.get(with_name))
                                cls__init__(inner_self, *args, **kwargs)

                            setattr(icls, '__init__', __init__)
                            return icls

                    return inner_cdec
                else:
                    def inner_cdec(icls):
                        setattr(icls, inject_value, self.get(with_name))
                        return icls

                    return inner_cdec

            elif asProperty:
                setattr(cls, inject_value, tangential_property)

            elif atInit:
                cls__init__ = cls.__init__
                if atInit == 'after':
                    @functools.wraps(cls__init__)
                    def __init__(inner_self, *args, **kwargs):
                        cls__init__(inner_self, *args, **kwargs)
                        setattr(inner_self, inject_value, self.get(with_name))
                else:
                    @functools.wraps(cls__init__)
                    def __init__(inner_self, *args, **kwargs):
                        setattr(inner_self, inject_value, self.get(with_name))
                        cls__init__(inner_self, *args, **kwargs)

                setattr(cls, '__init__', __init__)

            else:
                setattr(cls, inject_value, self.get(with_name))

            return cls

        return cdecorator

    def _get(self, paths):
        secrets = self.dynamic_config.secrets
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
        # error on unexpected keys to prevent forgetting variables:
        raise NotImplementedError

    def _make_dynamic(self):
        return {'auth-stores': {'secrets': {'path': '{:user-config-path}/orthauth/secrets.yaml'}},
                'auth-variables': {var:None for var in self.get_blob('auth-variables')}}

    def _serialize_user_config(self, format):
        config = self._make_dynamic()
        return self._dump(config, format)

    def write_user_config(self, *, format=None, dcp=None):
        # NOTE user config cannot write itself
        dcps = self.dynamic_config_paths
        for _d in dcps:  # if any config already exists exit
            if _d.exists():
                raise exc.ConfigExistsError('{_d}')

        if dcp is None:
            dcp = self.dynamic_config_path

        if format is not None:
            dcp = dcp.with_suffix('.' + format)
            if dcp not in dcps:
                # FIXME we do need to support .* or {yaml,py,lisp,json}
                raise TypeError(f'{dcp} not one of the expected formats {dcps}')
        else:
            format = dcp.suffix.strip('.')

        if not dcp.parent.exists():
            dcp.parent.mkdir(parents=True)

        with open(dcp, 'wt') as f:
            f.write(self._serialize_user_config(format))

    def get_path(self, variable_name):
        """ if you know a variable holds a path use this to autoconvert """
        var = self.get(variable_name, for_path=True)
        log.debug(type(var))
        log.debug(var)
        if isinstance(var, list):
            if not var:
                return

            first = None
            for v in var:
                p = self._pathit(v)
                print(p)
                if first is None:
                    first = p

                if p.exists():
                    return p
            else:
                return first

        else:
            return self._pathit(var)

    def get(self, variable_name, *args, **kwargs):
        """ look up the value of a variable name from auth store or config """
        av = self.get_blob('auth-variables')
        if variable_name not in av:
            error = None
            for i in self._include:
                try:
                    return i.get(variable_name)
                except KeyError as e:
                    error = e
            else:
                if error is not None:
                    raise error

        try:
            dvar_config = self.dynamic_config.get_blob('auth-variables', variable_name)
            if dvar_config is None:
                dvar_config = {}
                f1 = True
            else:
                f1 = False
        except KeyError as e:
            dvar_config = {}
            f1 = e

        try:
            var_config = av[variable_name]
            f2 = False
        except KeyError as e:
            var_config = {}
            f2 = e

        if f1 and f2:
            raise f2 from f1

        defaults = []
        if not isinstance(dvar_config, dict):
            if isinstance(dvar_config, list):
                if ('for_path' not in kwargs or not kwargs['for_path']):
                    log.warning(f'attempting to get a default value for {variable_name} '
                                'that is a list did you want get_path?')

                defaults.extend(dvar_config)
            else:
                defaults.append(dvar_config)

            dvar_config = {}

        if not isinstance(var_config, dict):
            if isinstance(var_config, list):
                if ('for_path' not in kwargs or not kwargs['for_path']):
                    log.warning(f'attempting to get a default value for {variable_name} '
                                'that is a list did you want get_path?')

                defaults.extend(var_config)
            else:
                defaults.append(var_config)

            var_config = {}
        elif 'default' in var_config:
            d = var_config['default']
            if isinstance(d, list):
                defaults.extend(d)
            else:
                defaults.append(d)

        envars = self._envars(dvar_config)
        envars += self._envars(var_config)
        paths = self._paths(dvar_config)
        paths += self._paths(var_config)

        if 'for_path' in kwargs and kwargs['for_path']:
            def get_default(d):
                return d
        else:
            def get_default(d):
                return str(d[0])

        for f, v in zip((getenv, self._get, get_default),
                        (envars, paths, defaults)):
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
                'ssh-config': self._ssh_config,
            }[type_]
        except KeyError as e:
            raise exc.UnknownAuthStoreType(type_)

    def _authinfo(self, blob):
        return Authinfo(self._blob_path(blob))

    def _secrets(self, blob):
        return Secrets(self._blob_path(blob))

    def _mypass(self, blob):
        return Mypass(self._blob_path(blob))

    def _ssh_config(self, blob):
        return SshConfig(self._blob_path(blob))

    def _blob_path(self, blob):
        return self._pathit(blob['path'])

    @property
    def secrets(self):
        """ default failover for paths without explicit management """
        return self._secrets(self.get_blob('auth-stores', 'secrets'))

    @property
    def _path_sources(self):
        # FIXME from type reads twice, should only read once
        try:
            path_data = self.get_blob('path-sources')
        except KeyError:
            return {}

        store_data = self.get_blob('auth-stores')
        out = {}
        for raw_path, type_ in path_data.items():
            try:
                names = tuple(next(parse_paths([raw_path])))
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


class Mypass:
    def __init__(self, path):
        if isinstance(path, str):
            path = pathlib.Path(path)

        self._path = path

    def __call__(self, *names):
        raise NotImplementedError('TODO')


class SshConfig:
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
        """ Fail early and often when missing a file that is supposed to exist """
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
