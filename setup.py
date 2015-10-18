
import os
from setuptools import setup


def safe_read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return ""


setup(name="apython",
      version="0.1.0",
      packages=["apython"],
      entry_points={'console_scripts': ['apython = apython:main']},

      classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
      ],


      license="GPLv3",
      description="Asynchronous Python interpreter",
      long_description=safe_read("README.md"),

      author="Vincent Michel",
      author_email="vxgmichel@gmail.com",
      )
