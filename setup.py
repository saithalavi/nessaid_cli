# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import os
import sys
import shutil
from setuptools import setup


pkg_name = 'nessaid_cli'
test_pkg_name = 'nessaid_cli_tests'
sub_packages = ['binding_parser', 'tokenizer']

install_packages = [pkg_name, test_pkg_name] + [pkg_name + "." + sub_pkg for sub_pkg in sub_packages]

clanup_dirs = ['build', 'dist', pkg_name + '.egg-info']


def do_cleanup_fixes():
    dir_content = os.listdir()
    for d in clanup_dirs:
        if d in dir_content:
            try:
                shutil.rmtree(d)
            except Exception:
                pass


long_description = """Nessaid CLI Framework

This package implements a grammar specification and tools to compile the grammar and use it for driving CLIs.
The CLI commands can be expressed in grammar with the support for custom tokens with suggestion and autocompletion.

The grammar specification is parsed with PLY python package and the CLI objects are implemented on top of readline.
The command loop is in async mode.

Requirements

asyncio: The commandline interpreter will be looping for console input in async mode

ply: The lex-yacc like implementation of python. Will be used for parsing the grammar specification
and tokenizing the line input

pyreadline: For windows platforms. This is the readline implementation for windows platforms
Enduser Utilities

This package provides two classes for CLI building. NessaidCmd is intended to work
like the standard Cmd class for simple CLI designs.
It is a stripped down sub class of the more robest NessaidCli class.

NessaidCmd: The basic Cmd like tool for end user.
The CLI command handlers are defined as python methods with chosen prefix and the
grammar definitions to drive them are expressed as the method docstring.

NessaidCli: The generic base class for the CLI impelemntation.
NessaidCmd is the stripped down version as an alternative for the default Cmd implementation
"""

install_requires = [
    "asyncio",
    "ply",
]

if os.name == 'nt':
    install_requires.append("pyreadline")

setup(
    name=pkg_name,
    version='2.1.0',
    url='https://github.com/saithalavi/nessaid_cli',
    description="Nessaid's CLI tools",
    long_description=long_description,
    author='Saithalavi M',
    author_email='saithalavi@gmail.com',
    packages=install_packages,
    include_package_data=True,
    install_requires=install_requires,
    python_requires='>=3',
    keywords='cli parser cli-builder',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
    project_urls = {
        'Documentation': 'https://github.com/saithalavi/nessaid_cli/blob/master/README.md',
        'Source': 'https://github.com/saithalavi/nessaid_cli',
        'Tracker': 'https://github.com/saithalavi/nessaid_cli/issues',
    },
    test_suite="nessaid_cli_tests",
)

if __name__ == '__main__':
    if 'clean' in sys.argv and 'install' not in sys.argv:
        do_cleanup_fixes()