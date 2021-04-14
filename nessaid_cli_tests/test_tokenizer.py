# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import inspect
import unittest

from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer


class TokenizerTest1(unittest.TestCase):

    def test_basic_tokens(self):

        input_and_tokens = [
            ('', []),
            (' ', []),
            ('" "', ['" "']),
            ('a', ['a']),
            ('abc', ['abc']),
            ('abc ', ['abc']),
            (' abc', ['abc']),
            (' abc ', ['abc']),
            ('123', ['123']),
            ('123 123', ['123', '123']),
            ('123  123', ['123', '123']),
            ('123    123', ['123', '123']),
            ('123    "123"', ['123', '"123"']),
            ('123    " 123"', ['123', '" 123"']),
            ('123    "123 "', ['123', '"123 "']),
            ('123    " 123 "', ['123', '" 123 "']),
            ('123    "123"abc', ['123', '"123"', 'abc']),
            ('123    "123" abc', ['123', '"123"', 'abc']),
            ('123    " 123"    abc', ['123', '" 123"', 'abc']),
            ('123    "123 "abc', ['123', '"123 "', 'abc']),
            ('123    " 123 " abc', ['123', '" 123 "', 'abc']),
            ('"123"', ['"123"']),
            ('"\\"', ['"\\"']),
            ('"\\\\\\"', ['"\\\\\\"']),
            ('"\\t"', ['"\\t"']),
            ('"\\n"', ['"\\n"']),
            ('"\\""', ['"\\""']),
            ('"\\"\\""', ['"\\"\\""']),\
            ('"\\\\\\t\\n\\""', ['"\\\\\\t\\n\\""']),
            ('"abc 123"', ['"abc 123"']),
            ('"abc 123', ['"abc 123']),
            ('"abc 123 "123', ['"abc 123 "', '123']),
            ('"abc 123 " 123', ['"abc 123 "', '123']),
            ('"abc 123 "  123', ['"abc 123 "', '123']),
            ('"abc 123 "   123', ['"abc 123 "', '123']),
        ]

        parser = NessaidCliTokenizer()

        for inp, out in input_and_tokens:
            tokens = parser.parse(inp)

            info = "\n\nFunction: {}".format(inspect.stack()[0][3])
            info += "\ninput: {}".format(inp)
            info += "\nrepr(input): {}".format(repr(inp))
            info += "\ntokens: {}".format(tokens)
            info += "\nExpected tokens: {}".format(repr(out))

            assert out == tokens, "Expected tokens mismatch:" + info


testcase1 = unittest.TestLoader().loadTestsFromTestCase(TokenizerTest1)
tokenizer_test = unittest.TestSuite([testcase1])