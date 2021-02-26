# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

MATCH_SUCCESS = 'success'
MATCH_FAILURE = 'failure'
MATCH_PARTIAL = 'partial'
MATCH_AMBIGUOUS = 'ambigous'

TOO_MANY_COMPLETIONS = -1


class TokenClassDef():

    def __init__(self, classname, arglist):
        self._classname = classname
        self._arglist = arglist

    @property
    def classname(self):
        return self._classname

    @property
    def arglist(self):
        return self._arglist

    def as_dict(self):
        return {
            "classname": self._classname,
            "arglist": self._arglist
        }

    @staticmethod
    def from_dict(d):
        elem = TokenClassDef(d["classname"], d["arglist"])
        return elem


class CliToken():

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name

    def __str__(self):
        return self.__repr__()

    def get_value(self, match_string=None):
        if self.completable:
            _, completions = self.complete(match_string)
            if len(completions) == 1:
                return completions[0]
            elif self.match(match_string) == MATCH_SUCCESS:
                return match_string
        else:
            if self.match(match_string) == MATCH_SUCCESS:
                return match_string
        raise ValueError("Fix matching logic for this token: {}".format(self.__class__.__name__))

    @property
    def name(self):
        return self._name

    @property
    def helpstring(self):
        return self._name

    @property
    def completable(self):
        return True

    def match(self, token_input):
        if self._name == token_input:
            return MATCH_SUCCESS
        elif self._name.startswith(token_input):
            return MATCH_PARTIAL
        else:
            return MATCH_FAILURE

    def complete(self, token_input):
        if not token_input:
            return 1, [self._name]
        elif self._name.startswith(token_input):
            return 1, [self._name]
        else:
            return 0, []


class AlternativeStringsToken(CliToken):

    def __init__(self, name, alternatives, *args):
        super().__init__(name)
        if (isinstance(alternatives, list) or
            isinstance(alternatives, set) or
            isinstance(alternatives, tuple)):
            self._alternatives = list(alternatives)
        elif args:
            self._alternatives = [alternatives] + list(args)
        else:
            self._alternatives = []

    @property
    def helpstring(self):
        return "Any one of: {}".format(set(self._alternatives))

    @property
    def completable(self):
        return True

    def complete(self, token_input):
        if not token_input:
            return len(self._alternatives), list(self._alternatives)
        completions = set()
        for e in self._alternatives:
            if token_input and e.startswith(token_input):
                completions.add(e)
        return len(completions), list(completions)

    def match(self, token_input):
        if token_input and token_input in  self._alternatives:
            return MATCH_SUCCESS
        n, completions = self.complete(token_input)
        if n == TOO_MANY_COMPLETIONS:
            return MATCH_PARTIAL
        if not completions:
            return MATCH_FAILURE
        elif len(completions) == 1:
            return MATCH_SUCCESS
        else:
            return MATCH_PARTIAL


class StringToken(CliToken):

    def __init__(self, name):
        super().__init__(name)

    @property
    def helpstring(self):
        return "Any string"

    @property
    def completable(self):
        return False

    def complete(self, token_input):
        return TOO_MANY_COMPLETIONS, []

    def match(self, token_input):
        return MATCH_PARTIAL

    def get_value(self, match_string=None):
        if isinstance(match_string, str):
            if match_string.startswith('"'):
                match_string = match_string[1:]
            if match_string.endswith('"'):
                match_string = match_string[:-1]
            return match_string
        return None


class RangedStringToken(StringToken):

    def __init__(self, name, min_len, max_len):
        min
        super().__init__(name)
        self._min_len = min(int(min_len), int(max_len))
        self._max_len = max(int(min_len), int(max_len))

        if (self._min_len < 0) or (self._max_len < 0):
            raise ValueError("Negative size")

    @property
    def helpstring(self):
        return "Any string of length ({}-{})".format(self._min_len, self._max_len)

    @property
    def completable(self):
        return False

    def complete(self, token_input):
        return TOO_MANY_COMPLETIONS, []

    def get_value(self, match_string=None):
        s = super().get_value(match_string)
        if isinstance(s, str):
            if len(s) >= self._min_len and len(s) <= self._max_len:
                return s
        return None

    def match(self, token_input):
        val = super().get_value(token_input)
        if len(val) > self._max_len:
            return MATCH_FAILURE
        if len(val) == self._max_len:
            return MATCH_SUCCESS
        return MATCH_PARTIAL


class RangedIntToken(CliToken):

    def __init__(self, name, start, end, max_suggestions=10):
        start = int(start)
        end = int(end)
        super().__init__(name)
        self._start = min(start, end)
        self._end = max(start, end)
        self._max_suggestions = max_suggestions

    @property
    def helpstring(self):
        return "An integer between {} and {}".format(self._start, self._end)

    def get_value(self, match_string=None):
        try:
            number = int(match_string)
            if number >= self._start and number <= self._end:
                return number
        except Exception:
            pass
        return None

    @property
    def completable(self):
        return True

    def _complete(self, min_limit, max_limit, number):

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

    def match(self, token_input):
        if isinstance(token_input, str):
            n, comps = self.complete(token_input)
            if n > 1 or n == TOO_MANY_COMPLETIONS:
                return MATCH_PARTIAL
            elif n == 1:
                return MATCH_SUCCESS
        return MATCH_FAILURE

    def complete(self, token_input):
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
                n, comps = self._complete(*comp_args)
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
                    number = int(token_input)
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

                    n, comps = self._complete(*comp_args)
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
                    n, comps = self._complete(*comp_args)
                    if n > 0 and not comps:
                        return TOO_MANY_COMPLETIONS, []
                    return n,  [str(c) for c in comps]


class RangedDecimalToken(CliToken):

    def __init__(self, name, start, end):
        start = float(start)
        end = float(end)
        super().__init__(name)
        self._start = min(start, end)
        self._end = max(start, end)

    @property
    def helpstring(self):
        return "A decimal number between {} and {}".format(self._start, self._end)

    @property
    def completable(self):
        return False

    def complete(self, token_input):
        return 0, []

    def match(self, token_input):
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

    def get_value(self, match_string=None):
        try:
            number = float(match_string)
            if number >= self._start and number <= self._end:
                return number
        except Exception:
            pass
        return None
