
# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys


class ExtendedString(str):

    def __new__(cls, value, *args, **kwargs):
    	return super(ExtendedString, cls).__new__(cls, value)

    def __init__(self, value, *args, **kwargs):
        self._args = args
        for key, value in kwargs.items():
            setattr(self, key, value)


class StdStreamsHolder():

    def init_streams(self, stdin=None, stdout=None, stderr=None):
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr

    @property
    def stdin(self):
        return self._stdin if self._stdin is not None else sys.stdin

    @property
    def stdout(self):
        return self._stdout if self._stdout is not None else sys.stdout

    @property
    def stderr(self):
        return self._stderr if self._stderr is not None else sys.stderr

    def print(self, *args):
        print(*args, file=self.stdout)

    def error(self, *args):
        print(*args, file=self.stderr)

