# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import os
import string
import fnmatch
import platform
from pathlib import Path

from nessaid_cli.utils import (
    convert_to_cli_string,
    convert_to_python_string
)


MATCH_SUCCESS = 'success'
MATCH_FAILURE = 'failure'
MATCH_PARTIAL = 'partial'
MATCH_AMBIGUOUS = 'ambigous'

TOO_MANY_COMPLETIONS = -1


class _NullTokenValue():

    __instance = None

    @staticmethod
    def getInstance():
        if _NullTokenValue.__instance == None:
            _NullTokenValue()
        return _NullTokenValue.__instance

    def __init__(self):
        if _NullTokenValue.__instance != None:
            raise Exception("This class is a singleton!")
        _NullTokenValue.__instance = self

    def __repr__(self):
        return "< Null Token Value >"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, rhs):
        if isinstance(rhs, _NullTokenValue):
            return True
        return False

    def __ne__(self, rhs):
        if isinstance(rhs, _NullTokenValue):
            return False
        return True

    def is_(self, rhs):
        if isinstance(rhs, _NullTokenValue):
            return True
        return False

    def is_not(self, rhs):
        if isinstance(rhs, _NullTokenValue):
            return False
        return True

    def __nonzero__(self):
        return False

    def __bool__(self):
        return False


NullTokenValue = _NullTokenValue.getInstance()


class CliToken():

    def __init__(self, name, helpstring=None, cli=None): # noqa
        self._name = name
        self._helpstring = helpstring
        self._cli_string = convert_to_cli_string(name)

    def __repr__(self):
        return self._cli_string

    def __str__(self):
        return self.__repr__()

    @property
    def case_insensitive(self):
        return False

    @property
    def cacheable(self):
        return True

    async def get_value(self, match_string=None, cli=None):
        if self.completable:
            _, completions = await self.complete(match_string, cli=cli)
            if len(completions) == 1:
                return convert_to_python_string(completions[0], cli=cli)
            elif await self.match(match_string, cli=cli) == MATCH_SUCCESS:
                return convert_to_python_string(match_string, cli=cli)
        else:
            if await self.match(match_string, cli=cli) == MATCH_SUCCESS:
                return convert_to_python_string(match_string, cli=cli)
        return NullTokenValue

    async def get_helpstring(self, match_string=None, cli=None): # noqa
        return self.helpstring

    @property
    def name(self):
        return self._name

    @property
    def helpstring(self):
        if self._helpstring is None:
            return self._cli_string
        return str(self._helpstring)

    @property
    def completable(self):
        return True

    async def match(self, token_input, cli=None): # noqa
        if self._cli_string == token_input:
            return MATCH_SUCCESS
        elif self._cli_string.startswith(token_input):
            return MATCH_PARTIAL
        else:
            return MATCH_FAILURE

    async def complete(self, token_input, cli=None): # noqa
        if not token_input:
            return 1, [self._cli_string]
        elif self._cli_string.startswith(token_input):
            return 1, [self._cli_string]
        else:
            return 0, []

    @staticmethod
    async def complete_from_multiple(options, token_input, cli=None): # noqa
        if not token_input:
            return len(options), list(options)
        completions = set()
        for e in options:
            if token_input and e.startswith(token_input):
                completions.add(e)
        return len(completions), list(completions)

    @staticmethod
    async def match_from_multiple(options, token_input, cli=None):
        if token_input and token_input in options:
            return MATCH_SUCCESS
        n, completions = await CliToken.complete_from_multiple(options, token_input, cli=cli)
        if n == TOO_MANY_COMPLETIONS:
            return MATCH_PARTIAL
        if not completions:
            return MATCH_FAILURE
        elif len(completions) == 1:
            return MATCH_SUCCESS
        else:
            return MATCH_PARTIAL


class AlternativeStringsToken(CliToken):

    def __init__(self, name, alternatives, *args, cli=None, helpstring=None):
        super().__init__(name, cli=cli, helpstring=helpstring)
        if (isinstance(alternatives, list) or
            isinstance(alternatives, set) or
            isinstance(alternatives, tuple)):
            self._alternatives = list(alternatives)
        elif args:
            self._alternatives = [alternatives] + list(args)
        else:
            self._alternatives = [alternatives]
        self._cli_strings = [convert_to_cli_string(s) for s in self._alternatives]

    @property
    def helpstring(self):
        return self._helpstring or "Any one of: {}".format(set(self._cli_strings))

    @property
    def completable(self):
        return True

    async def complete(self, token_input, cli=None):
        return await CliToken.complete_from_multiple(self._cli_strings, token_input, cli=cli)

    async def get_helpstring(self, match_string=None, cli=None):
        _, matches = await self.complete(match_string, cli)
        if matches:
            if len(matches) == 1:
                return matches[0]
            return "Any one of: {}".format(set(matches))
        return self.helpstring

    async def get_value(self, match_string=None, cli=None):
        v = await super().get_value(match_string, cli=cli)
        return v

    async def match(self, token_input, cli=None):
        return await CliToken.match_from_multiple(self._cli_strings, token_input, cli=cli)


class StringToken(CliToken):

    def __init__(self, name, cli=None, helpstring=None):
        super().__init__(name, cli=cli, helpstring=helpstring)

    @property
    def helpstring(self):
        return self._helpstring or "Any string"

    @property
    def completable(self):
        return False

    async def complete(self, token_input, cli=None): # noqa
        return TOO_MANY_COMPLETIONS, []

    async def match(self, token_input, cli=None): # noqa
        return MATCH_PARTIAL

    async def get_value(self, match_string=None, cli=None): # noqa
        if isinstance(match_string, str):
            if match_string.startswith('"'):
                match_string = match_string[1:]
            if match_string.endswith('"'):
                match_string = match_string[:-1]
            return match_string
        return NullTokenValue


class RangedStringToken(StringToken):

    def __init__(self, name, min_len, max_len, cli=None, helpstring=None):
        super().__init__(name, cli=cli, helpstring=helpstring)
        self._min_len = min(int(min_len), int(max_len))
        self._max_len = max(int(min_len), int(max_len))

        if (self._min_len < 0) or (self._max_len < 0):
            raise ValueError("Negative size")

    @property
    def helpstring(self):
        return self._helpstring or "Any string of length ({}-{})".format(self._min_len, self._max_len)

    @property
    def completable(self):
        return False

    async def complete(self, token_input, cli=None): # noqa
        return TOO_MANY_COMPLETIONS, []

    async def get_value(self, match_string=None, cli=None):
        s = await super().get_value(match_string, cli=cli)
        if isinstance(s, str):
            if len(s) >= self._min_len and len(s) <= self._max_len:
                return s
        return NullTokenValue

    async def match(self, token_input, cli=None):
        val = await super().get_value(token_input, cli=cli)
        if len(val) > self._max_len:
            return MATCH_FAILURE
        if len(val) == self._max_len:
            return MATCH_SUCCESS
        return MATCH_PARTIAL


class RangedIntToken(CliToken):

    def __init__(self, name, start, end, max_suggestions=10, cli=None, helpstring=None):
        start = int(start)
        end = int(end)
        super().__init__(name, cli=cli, helpstring=helpstring)
        self._start = min(start, end)
        self._end = max(start, end)
        self._max_suggestions = max_suggestions

    @property
    def helpstring(self):
        return self._helpstring or "An integer between {} and {}".format(self._start, self._end)

    async def get_value(self, match_string=None, cli=None): # noqa
        try:
            if match_string.isnumeric():
                number = int(match_string)
                if number >= self._start and number <= self._end:
                    return number
        except Exception:
            pass
        return NullTokenValue

    @property
    def completable(self):
        return True

    async def _complete(self, min_limit, max_limit, number):

        if number == 0:
            if (max_limit - min_limit + 1) > self._max_suggestions:
                return max_limit - min_limit + 1, []
            return max_limit - min_limit + 1, list(range(min_limit, max_limit + 1))

        if number > max_limit:
            return 0, []

        min_len = len(str(min_limit))
        max_len = len(str(max_limit))
        number_len = len(str(number))

        count = 0
        completions = []
        min_num = number
        max_num = number
        num_len = number_len
        power = 10

        if num_len < min_len:
            while num_len < min_len:
                min_num = min_num * 10
                max_num = min_num + power - 1
                num_len += 1
                power *= 10

        if num_len == min_len:
            if num_len == max_len and (max_num < min_limit or min_num > max_limit):
                return 0, []
            else:
                lower_limit = max(min_limit, min_num)
                upper_limit = min(max_limit, max_num)
                count = len(range(lower_limit, upper_limit + 1))
                if count > self._max_suggestions:
                    return count, []
                completions = list(range(lower_limit, upper_limit + 1))
                if num_len == max_len or count > self._max_suggestions:
                    return count, completions
        else:
            count = 1
            completions = [number]

        num_len = num_len + 1
        min_num = min_num * 10
        max_num = min_num + power - 1

        while num_len < max_len:
            count += power
            if count > self._max_suggestions:
                return count, []

            completions += list(range(min_num, max_num + 1))
            num_len += 1
            power = 10 ** (num_len - number_len)
            min_num = min_num * 10
            max_num = min_num + power - 1

        if min_num <= max_limit and num_len == max_len:
            count += len(range(min_num, min(max_num, max_limit) + 1))
            if count > self._max_suggestions:
                return count, []
            completions += list(range(min_num, min(max_num, max_limit) + 1))

        return count, completions

    async def match(self, token_input, cli=None):
        if isinstance(token_input, str):
            n, _comps = await self.complete(token_input, cli=cli) # noqa
            if n > 1 or n == TOO_MANY_COMPLETIONS:
                return MATCH_PARTIAL
            elif n == 1:
                return MATCH_SUCCESS
        return MATCH_FAILURE

    async def complete(self, token_input, cli=None): # noqa
        if isinstance(token_input, str) and str:
            count = 0
            comps = []

            if token_input == '-':
                if self._start >= 0:
                    return 0, []
                if self._end >= 0:
                    comp_args = [0, -self._start, 0]
                else:
                    comp_args = [-self._end, -self._start, 0]
                n, comps = await self._complete(*comp_args)
                if n > 0 and not comps:
                    return TOO_MANY_COMPLETIONS, []
                return n, [-c for c in comps]
            elif token_input == '':
                count = self._end - self._start + 1
                if count > 10:
                    return count, []
                elif count == 1:
                    return 1, [str(self._start)]
                elif count == 0:
                    return 0, []
                if count > self._max_suggestions:
                    comps = []
                else:
                    comps = list(range(self._start, self._end + 1))
                return count, comps

            else:
                try:
                    if token_input.isnumeric():
                        number = int(token_input)
                    else:
                        return 0, []
                except Exception:
                    return 0, []

                if number < 0 or token_input.startswith("-"):
                    if number == 0 and self._start == 0:
                        return 1, ["0"]
                    if self._start >= 0:
                        return 0, []
                    if self._end >= 0:
                        comp_args = [0, -self._start, -number]
                    else:
                        comp_args = [-self._end, -self._start, -number]

                    n, comps = await self._complete(*comp_args)
                    if n > 0 and not comps:
                        return TOO_MANY_COMPLETIONS, []
                    return n, [str(-c) for c in comps]
                else:
                    if self._end < 0:
                        return 0, []

                    if self._start <= 0:
                        comp_args = [0, self._end, number]
                    else:
                        comp_args = [self._start, self._end, number]
                    n, comps = await self._complete(*comp_args)
                    if n > 0 and not comps:
                        return TOO_MANY_COMPLETIONS, []
                    return n,  [str(c) for c in comps]


class RangedDecimalToken(CliToken):

    def __init__(self, name, start, end, cli=None, helpstring=None):
        start = float(start)
        end = float(end)
        super().__init__(name, cli=cli, helpstring=helpstring)
        self._start = min(start, end)
        self._end = max(start, end)

    @property
    def helpstring(self):
        return self._helpstring or "A decimal number between {} and {}".format(self._start, self._end)

    @property
    def completable(self):
        return False

    async def complete(self, token_input, cli=None): # noqa
        return 0, []

    async def match(self, token_input, cli=None): # noqa
        if isinstance(token_input, str):
            if token_input == "":
                return MATCH_PARTIAL
            if token_input == "-":
                if self._start >= 0 :
                    return MATCH_FAILURE
                return MATCH_PARTIAL
            try:
                decimal = float(token_input)
            except Exception:
                return MATCH_FAILURE
            if decimal > 0 and decimal > self._end:
                return MATCH_FAILURE
            if decimal < 0 and decimal < self._start:
                return MATCH_FAILURE
            return MATCH_PARTIAL
        return MATCH_FAILURE

    async def get_value(self, match_string=None, cli=None): # noqa
        try:
            number = float(match_string)
            if number >= self._start and number <= self._end:
                return number
        except Exception:
            pass
        return NullTokenValue


class PathTokenPath():

    def __init__(self, path, path_string, partial=False):
        self.path = path
        self.path_string = path_string
        self.partial = partial
        self.is_dir = path.is_dir()
        self.exists = path.exists()
        self.has_dir_completion = False

    def __repr__(self):
        return "{}: {}".format(self.path, self.path_string)

    def __str__(self):
        return "{}: {}".format(self.path, self.path_string)


class BooleanToken(StringToken):

    def __init__(self, name, cli=None, helpstring=None):
        super().__init__(name, cli=cli, helpstring=helpstring)

    @property
    def completable(self):
        return True

    @property
    def case_insensitive(self):
        return True

    @property
    def helpstring(self):
        return self._helpstring or "True or False"

    async def complete(self, str_input, cli=None): # noqa
        if not str_input:
            return 2, ["True", "False"]
        elif str_input.lower() in ["true", "false"]:
            return 1, [str_input]
        elif "true".startswith(str_input.lower()):
            return 1, [str_input + "true"[len(str_input):]]
        elif "false".startswith(str_input.lower()):
            return 1, [str_input + "false"[len(str_input):]]
        return 0, []

    async def match(self, str_input, cli=None):
        n, _l = await self.complete(str_input, cli=cli) # noqa
        if n == 0:
            return MATCH_FAILURE
        elif n == 1:
            if str_input.lower() in ["true", "false"]:
                return MATCH_SUCCESS
        return MATCH_PARTIAL

    async def get_value(self, str_input, cli=None):
        n, l = await self.complete(str_input, cli=cli)
        if n == 1:
            if l[0].lower() == "true":
                return True
            return False
        return NullTokenValue


class PathToken(StringToken):

    ANY = 'path'
    FILE = 'file'
    DIRECTORY = 'directory'

    def __init__(self, name, pathtype=ANY, cli=None, helpstring=None):
        self._pathtype = pathtype
        self._is_windows = None
        super().__init__(name, cli=cli, helpstring=helpstring)

    def get_drives(self):
        drives = []
        if self.is_windows:
            for c in string.ascii_lowercase:
                if os.path.isdir(c + ':'):
                    drives.append(c + ':')
        return drives

    @property
    def completable(self):
        return True

    @property
    def is_windows(self):
        if self._is_windows is None:
            os_system = platform.system()
            if os_system.lower() == 'windows':
                self._is_windows = True
            else:
                self._is_windows = False
        return self._is_windows

    @property
    def case_insensitive(self):
        if self.is_windows:
            return True
        return False

    @property
    def helpstring(self):
        if self.is_windows:
            path_sep = "\\\\"
        else:
            path_sep = "/"
        return "A {}.".format(self._pathtype) + ' Start the input with quote (") and use {} as separator'.format(path_sep)

    def children(self, path):
        try:
            content = os.listdir(path)
            if "." in content:
                content.remove(".")
            if ".." in content:
                content.remove("..")
            return content
        except PermissionError:
            print("\nPermissionError on {}\n".format(path))
            return []

    async def get_value(self, str_input, cli=None): # noqa
        _m, n, l, _ = await self.lookup(str_input) # noqa
        if n == 0:
            return NullTokenValue
        elif n == 1:
            return l[0].path_string
        else:
            return str_input

    async def complete(self, str_input, cli=None): # noqa
        if str_input == "":
            return TOO_MANY_COMPLETIONS, []
        elif str_input == '"':
            if self.is_windows:
                path_sep = "\\\\"
            else:
                path_sep = "/"

            options = ['".', '"..', '"' + path_sep]
            children = self.children(os.path.curdir)
            options += ['"' + c for c in children]
            return len(options), options
        else:
            if str_input.startswith('"') and str_input.endswith('"') and len(str_input) > 1:
                path_complete = True
            else:
                path_complete = False
            m, n, l, path_sep = await self.lookup(str_input)

            if not path_complete:
                for elem in l.copy():
                    if elem.is_dir and elem.has_dir_completion:
                        children = self.children(elem.path)
                        for c in children:
                            path_string = elem.path_string + c
                            l += [PathTokenPath(Path(path_string), path_string)]

            if m == MATCH_PARTIAL and len(l) == 1:
                if l[0].is_dir and not l[0].has_dir_completion:
                    l.append(PathTokenPath(l[0].path, l[0].path_string + path_sep, partial=True))
                if not l[0].is_dir:
                    path_complete = True
                else:
                    if not l[0].has_dir_completion:
                        if l[0].path_string == os.path.curdir or l[0].path_string.endswith(path_sep + os.path.curdir):
                            p = l[0].path_string + os.path.curdir
                            l.append(PathTokenPath(Path(p), p, partial=True))
                    else:
                        if not self.children(l[0].path):
                            path_complete = True

            return n, ['"' + str(elem.path_string) + ('"' if path_complete else "") for elem in l]

    async def match(self, str_input, cli=None): # noqa

        if str_input.startswith('"') and str_input.endswith('"') and len(str_input) > 1:
            path_complete = True
        else:
            path_complete = False
        m, _n, l, _ = await self.lookup(str_input) # noqa
        if m == MATCH_PARTIAL and len(l) == 1:
            if path_complete:
                return MATCH_SUCCESS
            elif not l[0].is_dir:
                return MATCH_SUCCESS
        return m

    async def lookup(self, str_input):
        path_complete = False
        if str_input == "":
            return MATCH_PARTIAL, TOO_MANY_COMPLETIONS, [], os.path.pathsep

        if str_input.startswith('"'):
            str_input = str_input[1:]

            if str_input.endswith('"'):
                str_input = str_input[:-1]
                path_complete = True

        segments = str_input.split(os.path.sep)
        add_drive_mark = ""

        path_sep = "/"
        if not segments:
            if not self.is_windows:
                return MATCH_FAILURE, 0, [], path_sep
            segments = str_input.split("/")
            if not segments:
                return MATCH_FAILURE, 0, [], path_sep
        else:
            if self.is_windows:
                path_sep = "\\"

        path_string = ""
        partial_drive = None

        if segments[0] == "":
            if len(segments) == 1:
                path_string = ""
            else:
                path_string = path_sep
        elif self.is_windows:
            if len(segments[0]) == 2 and segments[0][1] == ":":
                path_string = segments[0]
                add_drive_mark = path_sep
            elif len(segments[0]) == 3 and segments[0][0] == "/" and segments[0][2] == ":":
                path_string = segments[0][1:]
                add_drive_mark = path_sep

        if path_string:
            path_objects = [PathTokenPath(Path(path_string + add_drive_mark), path_string)]
            if path_string == path_sep:
                path_objects[0].has_dir_completion = True
            segments.pop(0)
        else:
            path_objects = [PathTokenPath(Path(os.path.curdir), "")]
            if self.is_windows and len(segments) == 1 and not path_complete:
                if (segments[0].lower() + ":") in self.get_drives():
                    partial_drive = Path(segments[0] + ":\\")
                    partial_drive_str = segments[0] + ":"

        while segments:
            path_objects = [p for p in path_objects if p.is_dir and not p.partial]
            for p in path_objects:
                if p.path_string and not p.path_string.endswith(path_sep):
                    p.path_string += path_sep
                    p.has_dir_completion = True

            segment = segments.pop(0)
            if segment == "":
                break

            p.has_dir_completion = False

            if segment == ".":
                for p in path_objects:
                    p.path_string += "."
                continue
            elif segment == "..":
                for p in path_objects:
                    p.path_string += ".."
                    p.path = Path(p.path_string)
            elif segment == "*":
                opts = []
                for p in path_objects:
                    children = self.children(p.path)
                    for c in children:
                        path_string = p.path_string + c
                        opts.append(PathTokenPath(Path(path_string), path_string))
                path_objects = opts
            else:
                opts = []
                for p in path_objects:
                    children = self.children(p.path)
                    if self.case_insensitive:
                        exacts = [p.path_string + c for c in children if c.lower() == segment.lower()]
                    else:
                        exacts = [p.path_string + c for c in children if c == segment]

                    matches = [p.path_string + c for c in children if fnmatch.fnmatch(c, segment) and p.path_string + c not in exacts]
                    matches = list(set(matches + exacts))
                    opts += [PathTokenPath(Path(m), m) for m in matches]
                    if not path_complete:
                        if not self.case_insensitive:
                            path_strings = matches
                            partial_matches = [PathTokenPath(Path(p.path_string + c), p.path_string + c, partial=True) for c in children if c.startswith(segment) and p.path_string + c not in path_strings]
                        else:
                            path_strings = [m.lower() for m in matches]
                            partial_matches = [PathTokenPath(Path(p.path_string + c), p.path_string + c, partial=True) for c in children if c.lower().startswith(segment.lower()) and p.path_string.lower() + c.lower() not in path_strings]
                        opts += partial_matches

                if partial_drive:
                    path_objects = [PathTokenPath(partial_drive, partial_drive_str, partial=True)]
                    partial_drive = None
                else:
                    path_objects = []
                path_objects += opts

        dirs = [d for d in path_objects if d.is_dir]
        files = [f for f in path_objects if not f.is_dir]

        if (len(dirs) + len(files)) == 1:
            if (dirs + files)[0].partial or not path_complete:
                return MATCH_PARTIAL, 1, dirs + files, path_sep
            else:
                return MATCH_SUCCESS, 1, dirs + files, path_sep

        if (len(dirs) + len(files)) == 0:
            return MATCH_FAILURE, 0, [], path_sep
        return MATCH_PARTIAL, len(dirs) + len(files), (dirs + files), path_sep
