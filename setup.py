# encoding=UTF-8

# Copyright © 2014-2016 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
*python-afl* is an experimental module that enables
`American fuzzy lop`_ fork server and instrumentation for pure-Python code.

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/
'''

import distutils.core
import distutils.version
import sys

def uopen(path):
    if str is not bytes:
        return open(path, 'rt', encoding='UTF-8')
    else:
        return open(path, 'rt')

def get_version():
    with uopen('doc/changelog') as f:
        return f.readline().split()[1].strip('()')

classifiers = '''
Development Status :: 3 - Alpha
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Operating System :: POSIX
Programming Language :: Cython
Programming Language :: Python :: 2
Programming Language :: Python :: 3
Topic :: Software Development :: Quality Assurance
Topic :: Software Development :: Testing
'''.strip().splitlines()

meta = dict(
    name='python-afl',
    version=get_version(),
    license='MIT',
    description='American fuzzy lop fork server and instrumentation for pure-Python code',
    long_description=__doc__.strip(),
    classifiers=classifiers,
    url='http://jwilk.net/software/python-afl',
    author='Jakub Wilk',
    author_email='jwilk@jwilk.net',
)

if 'setuptools' in sys.modules and sys.argv[1] == 'egg_info':
    # We wouldn't normally want setuptools; but pip forces it upon us anyway,
    # so let's abuse it to instruct pip to install Cython if it's missing.
    distutils.core.setup(
        install_requires=['Cython>=0.19'],
        # Conceptually, “setup_requires” would make more sense than
        # “install_requires”, but the former is not supported by pip:
        # https://github.com/pypa/pip/issues/1820
        **meta
    )
    sys.exit(0)

try:
    import Cython
except ImportError:
    raise RuntimeError('Cython >= 0.19 is required')

try:
    cython_version = Cython.__version__
except AttributeError:
    # Cython prior to 0.14 didn't have __version__.
    # Oh well. We don't support such old versions anyway.
    cython_version = '0'
cython_version = distutils.version.LooseVersion(cython_version)
if cython_version < '0.19':
    raise RuntimeError('Cython >= 0.19 is required')

import Cython.Build

distutils.core.setup(
    ext_modules=Cython.Build.cythonize('afl.pyx'),
    scripts=['py-afl-fuzz'],
    **meta
)

# vim:ts=4 sts=4 sw=4 et
