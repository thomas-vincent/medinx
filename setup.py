#!/usr/bin/env python3

from setuptools import setup

# scripts = ['scripts/lsx', 'scripts/cdx', 'scripts/treex']
scripts = []
setup(name='medinx',
      version='0.1',
      description='metadata file manager',
      author='Thomas Vincent',
      author_email='thomas.tv.vincent@gmail.com',
      url='https://github.com/thomas-vincent/medinx',
      packages=['medinx'],      
      package_dir={'': 'python'},
      license='GPL3',
      scripts=scripts,
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Environment :: Console",
          "Intended Audience :: End Users/Desktop",
          "Intended Audience :: Information Technology",
          "Programming Language :: Python :: 3",
          "Operating System :: OS Independent",
          "Topic :: Utilities",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Natural Language :: English"],
      python_requires = '>= 3.6',
)
