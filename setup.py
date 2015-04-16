import distutils.core as distutils_core
import Cython.Build as cython_build

distutils_core.setup(
    name='python-afl',
    version='0.1',
    ext_modules=cython_build.cythonize('afl.pyx'),
)

# vim:ts=4 sts=4 sw=4 et
