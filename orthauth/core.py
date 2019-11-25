import os
import ast
import sys
import json
import inspect
import pathlib
import functools
import importlib
from pprint import pformat
from . import stores
from . import exceptions as exc
from .utils import branches, getenv, parse_paths
from .utils import log, logd

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
    return AuthConfig._from_relative_path(calling__file__,
                                          name,
                                          include=include,
                                          calling_module=calling_module)


class DecoBase:
    def environ(self, set_envar, from_name, when=True):
        """ in order to use orthauth with other projects that are not aware of
            its existence and that make use of environment variables orthauth
            can set the envar that the other project expects using a value from
            an orthauth managed auth store """
        raise NotImplementedError('TODO')

    def tangential_init(self, inject_value, with_name, when=True, after=False):
        """ tangential decorator that defaults to atInit since it is a common use case

            note that this can be used to monkey patch classes as well """
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
            try:
                return yaml.safe_load(f)
            except NameError as e:
                msg = (f'Module yaml was not found while tyring to load {self._path}\n'
                       'To resolve this issue reinstall orthauth with yaml '
                       'support enabled\n or reform your config to .py')
                raise ModuleNotFoundError(msg) from e

    @staticmethod
    def _envars(var_config):
        envars = []
        # env
        for evkey in ('environment-variables', 'env-vars', 'envars'):
            if evkey in var_config:
                ev = var_config[evkey]
                if isinstance(ev, str):
                    envars += ev.split(' ')
                elif isinstance(ev, list):
                    envars += ev
                else:
                    raise TypeError(f'unsupported type {type(ev)}\n{ev}')

        return envars

    @staticmethod
    def _paths(var_config):
        if 'config' in var_config:
            if [_ for _ in ('path', 'paths', 'paths-nested') if _ in var_config]:
                raise TypeError('can only have config or path, not both')

            return []

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

    @staticmethod
    def _single_alt_configs(var_config):
        if 'config' in var_config:
            if 'path' in var_config:
                raise TypeError('can only have config or path, not both')

            return var_config

    def _pathit(self, path_string):
        return self._pathit_relative(self._path.parent, path_string)

    def _pathit_relative(self, relative_base, path_string):
        if not isinstance(path_string, pathlib.Path):
            if '{:' in path_string:  # special paths  # FIXME vs startswith
                path_string = path_string.replace('{:', '{')
                path_string = path_string.format(**self._config_vars)

            path = pathlib.Path(path_string)
        else:
            path = path_string

        if path.parts[0] == ('~'):
            path = path.expanduser()

        if not path.is_absolute():
            path = relative_base / path

        if '..' in path.parts:
            path = path.resolve()

        return path

    @property
    def _config_vars(self):
        """ currently supported config vars

            cwd
            prefix
            user-cache-path
            user-config-path
            user-data-path
            user-log-path
        """
        if os.name != 'nt':
            if sys.platform == 'darwin':
                ucp = '~/Library/Application Support'
                udp = '~/Library/Application Support'
                uchp = '~/Library/Caches'
                ulp = '~/Library/Logs'
            else:
                ucp = '~/.config'
                udp = '~/.local/share'
                uchp = '~/.cache'
                ulp = '~/.cache/log'
        else:
            ucp = '~/AppData/Local'
            udp = ucp
            uchp = ucp
            ulp = '~/AppData/Local/Logs'

        return {'cwd': pathlib.Path.cwd(),
                'prefix': sys.prefix,
                'user-cache-path': uchp,
                'user-config-path': ucp,
                'user-data-path': udp,
                'user-log-path': ulp,
        }


class AuthConfig(DecoBase, ConfigBase):  # FIXME this is more a schema?
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
        self._dynamic_config = UserConfig(self)
        return self

    def __new__(cls, path, include=tuple()):
        self = super().__new__(cls, path, include=include)
        self._dynamic_config = UserConfig(self)
        return self

    @property
    def dynamic_config(self):
        dc = self._dynamic_config
        ac = dc.alt_config
        if ac:
            dc = ac
        
        return dc

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
        if var == [None]:
            return

        if isinstance(var, list):
            if not var:
                return

            first = None
            for v in var:
                if v is None:
                    msg = f'{variable_name} in {self._path}'
                    raise exc.SomethingWrongWithVariableInConfig(msg)

                p = self._pathit(v)
                if first is None:
                    first = p

                if p.exists():
                    return p
                else:
                    # never log v or any values derived from v as they
                    # might be secrets, the user will have to figure out
                    # where they messed up by looking at the configs directly
                    log.warning(f'path for {variable_name} does not exist, '
                                'did you enter a path: as a value?')
            else:
                return first

        else:
            return self._pathit(var)

    def get_default(self, variable_name, *args, **kwargs):
        av = self.get_blob('auth-variables')
        var_config = av[variable_name]

        defaults = []
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

        if defaults:
            return defaults[0]

    def get_path_default(self, variable_name):
        d = self.get_default(variable_name, for_path=True)
        if d is not None:
            return self._pathit(d)

    def get(self, variable_name, *args, **kwargs):
        """ look up the value of a variable name from auth store or config """
        for_path = 'for_path' in kwargs and kwargs['for_path']
        av = self.get_blob('auth-variables')
        if variable_name not in av:
            error = None
            for i in self._include:
                try:
                    return i.get(variable_name, **kwargs)
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
                if not for_path:
                    log.warning(f'attempting to get a default value for {variable_name} '
                                'that is a list did you want get_path?')

                defaults.extend(dvar_config)
            else:
                defaults.append(dvar_config)

            dvar_config = {}

        if not isinstance(var_config, dict):
            if isinstance(var_config, list):
                if not for_path:
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

        bads = self._single_alt_configs(var_config)  # for error purposes only
        if bads:
            msg = ('static configs should never define single atl configs\n'
                   f'{bads} in {self._path}')
            raise exc.BadAuthConfigFormatError(msg)

        alt = self._single_alt_configs(dvar_config), variable_name, for_path

        if for_path:
            get_dc = self.dynamic_config._get_path
            def get_default(d):
                return d
        else:
            get_dc = self.dynamic_config._get
            def get_default(d):
                if len(d) == 1 and d[0] is None:
                    return
                else:
                    return str(d[0])

        for f, v in zip((getenv,
                         get_dc,
                         self.dynamic_config._gsac_wrap,
                         get_default),
                        (envars, paths, alt, defaults)):
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

    @classmethod
    def _from_dynamic_alt_config(cls, path, static_config, rename=None):
        # TODO rename
        self = super().__new__(cls, path)
        if rename:
            self.__rename = rename
            self.load_type = self._rename_load_type

        self.static_config = static_config
        return self

    def _rename_load_type(self):
        blob = super().load_type()
        av = blob['auth-variables']
        log.debug(self.__rename)
        [log.debug(k) for k in av.keys()]
        for to, frm in self.__rename.items():
            if frm in av:
                av[to] = av.pop(frm)

        [log.debug(k) for k in av.keys()]
        return blob

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
        return stores.Authinfo(self._blob_path(blob))

    def _get_store(self, store, blob):
        path = self._blob_path(blob)
        try:
            return store(path)
        except FileNotFoundError as e:
            err = exc.SomethingWrongWithVariableInConfig(f'{path} in {self._path}')
            raise err from e

    def _secrets(self, blob):
        return self._get_store(stores.Secrets, blob)

    def _mypass(self, blob):
        return self._get_store(stores.Mypass, blob)

    def _ssh_config(self, blob):
        return self._get_store(stores.SshConfig, blob)

    def _blob_path(self, blob):
        return self._pathit(blob['path'])

    def get(self, variable_name, *args, **kwargs):
        """ look up the value of a variable name from auth store or config """
        # ah the problem of interleveing values from sources of different rank ...
        for_path = 'for_path' in kwargs and kwargs['for_path']
        var_config = self.get_blob('auth-variables', variable_name)
        if var_config is None:
            raise KeyError(variable_name)

        defaults = []
        if not isinstance(var_config, dict):
            if isinstance(var_config, list):
                if not for_path:
                    log.warning(f'attempting to get a default value for {variable_name} '
                                'that is a list did you want get_path?')

                defaults.extend(var_config)
            else:
                defaults.append(var_config)

            var_config = {}

        envars = self._envars(var_config)
        paths = self._paths(var_config)
        alt = self._single_alt_configs(var_config), variable_name, for_path

        if for_path:
            def get_default(d):
                return d
        else:
            def get_default(d):
                if len(d) == 1 and d[0] is None:
                    return
                else:
                    return str(d[0])

        for f, v in zip((getenv,
                         self._get_path if for_path else self._get,
                         self._gsac_wrap,
                         get_default),
                        (envars, paths, alt, defaults)):
            if v:
                SECRET = f(v)
                if SECRET is not None:
                    return SECRET

    def _get_path(self, paths):
        store_path, value = self._get_with_path(paths)
        return self._pathit_relative(store_path.parent, value)

    def _get(self, paths):
        _, value = self._get_with_path(paths)
        return value

    def _get_with_path(self, paths):
        secrets = self.secrets
        errors = []
        for names in paths:
            auth_store = self.path_source(*names)  # FIXME perf issue incoming
            try:
                return auth_store._path, auth_store(*names)
            except KeyError as e:
                errors.append(e)
                logd.error(f'broken path {names}')
                if auth_store != secrets:
                    try:
                        return secrets._path, secrets(*names)
                    except KeyError as e:
                        errors.append(e)

        if errors:
            raise KeyError(f'{[e.args[0] for e in errors]}') from errors[-1]

    def _gsac_wrap(self, args):
        return self._get_single_alt_config(*args)

    def _get_single_alt_config(self, blob, variable, for_path=False):
        # FIXME relative paths get funky here
        if blob:
            config = blob['config']
            path = self._pathit(config)
            rename = blob.get('rename', None)
            if rename is not None:
                variable = rename

            adc = self._from_dynamic_alt_config(path, self.static_config)
            return adc.get(variable, for_path=for_path)

    @property
    def _alt_config_path(self):
        blob = self.get_blob('alt-config')
        if not isinstance(blob, str):
            raise TypeError('only a single alt config is allowed')
        else:
            return self._pathit(blob)

    @property
    def _rename(self):
        blob = self.get_blob('rename')
        if not isinstance(blob, str):
            raise TypeError('only a single alt config is allowed')
        else:
            return self._pathit(blob)

    @property
    def alt_config(self):
        try:
            path = self._alt_config_path
            _test = self.load_type()
            _test.pop('alt-config')
            rename = _test.pop('rename', None)
            if _test:
                raise ValueError('configs with top level alt-config may '
                                 f'have only a rename section\n{_test}')

            return self._from_dynamic_alt_config(path, self.static_config, rename)
        except KeyError:
            pass

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
