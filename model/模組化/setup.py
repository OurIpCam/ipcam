from setuptools import setup
from Cython.Build import cythonize

setup(
    name="notify",
    ext_modules=cythonize("notify.py", language_level="3"),
    zip_safe=False,
)
