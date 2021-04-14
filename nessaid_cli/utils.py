
# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys


ESCAPED_CHAR_INPUTS = [
    '\\n',
    '\\0',
    '\\r',
    '\\t',
    '\\b',
    '\\v',
    '\\a',
    '\\"',
    '\\\\'
]


class ExtendedString(str):

    def __new__(cls, value, *args, **kwargs):
    	return super(ExtendedString, cls).__new__(cls, value)

    def __init__(self, value, *args, **kwargs):
        self._args = args
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def value(self):
        return str(self)


def convert_to_python_string(cli_string):

    converted_str = cli_string

    if hasattr(cli_string, "quoted") and cli_string.quoted:
        if converted_str.startswith('"'):
            converted_str = converted_str[1:]

        if not hasattr(cli_string, "quote_incomplete") or not cli_string.quote_incomplete:
            if converted_str.endswith('"'):
                converted_str = converted_str[:-1]

    if any(pattern in converted_str for pattern in ESCAPED_CHAR_INPUTS):
        parts = converted_str.split("\\\\")
        converted_parts = []
        for part in parts:
            part = part.replace("\\n", "\n")
            part = part.replace("\\0", "\0")
            part = part.replace("\\r", "\r")
            part = part.replace("\\t", "\t")
            part = part.replace("\\b", "\b")
            part = part.replace("\\v", "\v")
            part = part.replace("\\a", "\a")
            part = part.replace('\\"', '"')
            converted_parts.append(part)

        converted_str = "\\".join(converted_parts)
    return converted_str


def convert_to_cli_string(python_string):
    if any(c in python_string for c in ["\n", "\0", "\r", "\t", "\b", "\a", "\v", '"']):
        parts = python_string.split("\\")
        converted_parts = []
        for part in parts:
            part = part.replace("\n", "\\n")
            part = part.replace("\0", "\\0")
            part = part.replace("\r", "\\r")
            part = part.replace("\t", "\\t")
            part = part.replace("\b", "\\b")
            part = part.replace("\v", "\\v")
            part = part.replace("\a", "\\a")
            part = part.replace('"', '\\"')
            converted_parts.append(part)

        return ExtendedString('"' + "\\\\".join(converted_parts) + '"', quoted=True)
    return python_string


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

