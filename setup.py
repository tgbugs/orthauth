import re
from setuptools import setup


def find_version(filename):
    _version_re = re.compile(r"__version__ = ['\"](.*)['\"]")
    last = None  # match python semantics
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            last = version_match.group(1)

    return last


__version__ = find_version('orthauth/__init__.py')

with open('README.md', 'rt') as f:
    long_description = f.read()

yaml_requires = ['pyyaml']
sxpr_requires = ['sxpyr>=0.0.2']
tests_require = ['pytest'] + yaml_requires + sxpr_requires
setup(name='orthauth',
      version=__version__,
      description='A library to separate configuration and authentication from program logic',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/tgbugs/orthauth',
      author='Tom Gillespie',
      author_email='tgbugs@gmail.com',
      license='MIT',
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Operating System :: POSIX :: Linux',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
      ],
      keywords=('python orthogonal authentication '
                'config configuration management'),
      packages=[
          'orthauth',
      ],
      python_requires='>=3.6',
      tests_require=tests_require,
      install_requires=[],
      extras_require={'test': tests_require,
                      'yaml': yaml_requires,
                      'sxpr': sxpr_requires,
                     },
      scripts=[],
      entry_points={'console_scripts': [ ],},
     )
