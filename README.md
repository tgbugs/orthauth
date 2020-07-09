# orthauth
[![PyPI version](https://badge.fury.io/py/orthauth.svg)](https://pypi.org/project/orthauth/)
[![Build Status](https://travis-ci.org/tgbugs/orthauth.svg?branch=master)](https://travis-ci.org/tgbugs/orthauth)
[![Coverage Status](https://coveralls.io/repos/github/tgbugs/orthauth/badge.svg?branch=master)](https://coveralls.io/github/tgbugs/orthauth?branch=master)

A library to separate configuration and authentication from program logic

# THIS IS NOT ENCRYPTED
# THIS IS NOT A PASSWORD MANAGER
# THIS IS NOT A SECURE SECRET STORAGE SYSTEM
# YOU CAN SHOOT YOURSELF IN THE FOOT WITH THIS
There is **NO encryption** for secrets stored using orthauth.
Orthauth can source credientials from a variety of sources
but it is **INTENTIONALLY INSECURE**.

If you do not understand the [use case](#use-case) for this as well as the
risks if used outside a secure environment then DO NOT USE IT.
No one can help you if you get pwnd.

## Use case
The primary use case for `orthauth` is to keep api keys from leaking into
source code and winding up in public repositories. `orthauth` does not provide
operational security for any auth store that it uses. It is up to the user to
secure those and the systems they reside on as they see fit.

While `orthauth` attemts to prevent secrets from leaking via debug messages
or logging, it doesn't know anything about the secretness of the values it
returns, and once it has returned that value, it is up to the consuming code
to prevent the contents of the value from leaking.

`orthauth` is indented to unify two common ways managing configuration
variables and credentials: setting them environment variables, and including
them in a plain text file with permissions set to `0600` (and preferably kept
in a folder set to `0700`).

For example running a program in the following way
`export API_KEY=lolplzdonotstealthis; ./my-script-that-needs-the-key`
or using a file like `~/.pgpass` or emacs `.authinfo`. Note that
pgpass probably shouldn't be a source for most python implementations
because libraries like psycopg2 are able to read it directly. However in
other languages that do not have a library that supports reading from pgpass
directly, then pgpass would be a useful source.

By making it possible to provide credentials seemlessley in multiple ways
the hope is to reduce the use of different solutions in different environments
without incuring the massive complexity of maintaining a managed authentication
infrasturcture.

## Approach
1. Decorators  
2. A layer of indirection between names in a code base and config/secrets structure.
3. Be clear about what should be considered public information. Thus prevent anything
stored as a secret from being used as a key to find another secret.
4. Bare minimum to store static configuration information, anything more should
be implemented in the language consuming the config, not in the config.

## Currently supported config formats
| Format                     | Support         | Install                      |
| -------------------------- | --------------- | ---------------------------- |
| json                       | builtin         | `pip install orthauth`       |
| python dictionary literals | builtin         | `pip install orthauth`       |
| yaml                       | requires pyyaml | `pip install orthauth[yaml]` |

## Usage
```python
import orthauth as oa
auth = oa.AuthConfig('path/to/config.yaml')

@auth.tangential_init('api_key', 'some-service-api-key')
class ThatNeedsAuth:
    """ needs authenticated connection to some-service """

tna = ThatNeedsAuth()
print(tna.api_key)
```
Haven't been scared off yet?
See the [developer guide](./docs/guide.org) for more examples.
