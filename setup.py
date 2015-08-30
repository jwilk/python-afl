# encoding=UTF-8

# Copyright © 2014-2015 Jakub Wilk <jwilk@jwilk.net>
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
import Cython.Build

try:
    cython_version = Cython.__version__
except AttributeError:
    cython_version = '0'
cython_version = distutils.version.LooseVersion(cython_version)
if cython_version < '0.19':
    raise RuntimeError('Cython >= 0.19 is required')

def get_version():
    try:
        f = open('doc/changelog', encoding='UTF-8')
    except TypeError:
        f = open('doc/changelog')
    with f:
        return f.readline().split()[1].strip('()')

class lazylist(list):

    def __init__(self, obj):
        self._obj = obj

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, n):
        return self._obj[n]

    def __iter__(self):
        return iter(self._obj)

classifiers = '''
Development Status :: 2 - Pre-Alpha
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Operating System :: POSIX
Topic :: Software Development :: Quality Assurance
Topic :: Software Development :: Testing
'''.strip().splitlines()

distutils.core.setup(
    name='python-afl',
    version=get_version(),
    license='MIT',
    description='American fuzzy lop fork server and instrumentation for pure-Python code',
    long_description=__doc__.strip(),
    classifiers=classifiers,
    url='http://jwilk.net/software/python-afl',
    author='Jakub Wilk',
    author_email='jwilk@jwilk.net',
    ext_modules=lazylist(Cython.Build.cythonize('afl.pyx')),
    scripts=['py-afl-fuzz'],
)

# vim:ts=4 sts=4 sw=4 et
