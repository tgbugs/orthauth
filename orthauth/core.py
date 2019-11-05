import stat
import appdirs


class Secrets:
    def __init__(self, config):
        self.config = config
        if self.exists:
            fstat = os.stat(self.filename)
            mode = oct(stat.S_IMODE(fstat.st_mode))
            if mode != '0o600' and mode != '0o700':
                raise FileNotFoundError(f'Your secrets file {self.filename} '
                                        f'can be read by the whole world! {mode}')

    @property
    def filename(self):
        return self.config.secrets_file

    @property
    def exists(self):
        e = Path(self.filename).exists()
        if not e:
            log.warning(f'secrets file {self.filename} does not exist. '
                        'You can set an alternate path under the secrets_file: '
                        f'variable in {self.config.config_file}')

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
                    raise ValueError(f'WHY ARE YOU TRYING TO USE A SECRET {ANGRY} AS A NAME!?')
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
                current = Path(current).expanduser().as_posix()  # for consistency with current practice, keep paths as strings
            return current



