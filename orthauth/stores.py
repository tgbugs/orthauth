import os
import stat
import pathlib
from . import exceptions as exc
from .utils import QuietDict, log

try:
    import yaml  # FIXME DANGERZONE :/
except ImportError as e:
    pass


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
            if os.name == 'nt':
                log.warning('Make sure other user cannot read your secrets file '
                            'because right at the moment I don\'t know how to check.')
            else:
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
            # secrets could be exposted by brute force, but in this case it is ok
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
                keys = sorted(current.keys())
                ANGRIER = ['*' * len(k) for k in keys if k in av]
                if ANGRIER:
                    if len(ANGRIER) == 1:
                        msg = f'WHY ARE YOU TRYING TO USE A SECRET {ANGRIER[0]} AS A NAME!?'
                    else:
                        msg = ('WHY ARE YOU TRYING TO USE MULTIPLE (!!) '
                               f'SECRETS {" ".join(ANGRIER)} AS A NAME!?')

                    av = None
                    name = None
                    names = None
                    current = None
                    keys = None
                    del av
                    del name
                    del names
                    del current
                    del keys
                    raise exc.SecretAsKeyError()

                else:
                    msg = f'Your secret path is incomplete. Keys are {keys}'
                    av = None
                    name = None
                    names = None
                    current = None
                    del av
                    del name
                    del names
                    del current
                    raise ValueError(msg)

            if current is None:
                # empty secrets are an error
                msg = f'Value of secret at {names} is None.'
                av = None
                name = None
                names = None
                current = None
                del av
                del name
                del names
                del current
                raise ValueError(msg)

            return current


class Runtime(Secrets):

    exists = True
    _path = None

    def __init__(self, blob):
        self._sblob = QuietDict(blob)

    @property
    def name_id_map(self):
        return self._sblob
