from distutils.core import setup, Extension

setup(
    name='matrix',
    version='1.0',
    ext_modules=[
        Extension('matrix',
                  ['matrix.cpp'],
                  language='c++',
                  extra_compile_args=['-std=c++11'])
    ]
)
