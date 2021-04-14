# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys
import inspect
import asyncio
import unittest

from nessaid_cli.cmd import NessaidCmd
from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer

from nessaid_cli.tokens import (
    StringToken,
    RangedIntToken,
    BooleanToken,
    RangedStringToken,
)

from nessaid_cli_tests.test_utils import captured_output


class Cmd1(NessaidCmd):
    """
    token STRING_TOKEN StringToken();
    token BOOLEAN BooleanToken();
    token RANGED_STRING_TOKEN_1 RangedStringToken(5, 10);
    token RANGED_INT_TOKEN_1 RangedIntToken(0, 100);
    token RANGED_INT_TOKEN_2 RangedIntToken(1, 1000);
    token RANGED_INT_TOKEN_3 RangedIntToken(-100, -1);
    token RANGED_INT_TOKEN_4 RangedIntToken(-100, 100);
    token RANGED_INT_TOKEN_5 RangedIntToken(-100, 0);
    """

    def get_token_classes(self):
        return [
            StringToken,
            RangedStringToken,
            RangedIntToken,
            BooleanToken,
        ]

    def do_basic_1(self, cli_input, cli_output):
        """
        "input" << $cli_input = $1; $cli_output = "output"; >>
        """
        print("input:", cli_input)
        print("output:", cli_output)

    def do_types_1(self, cli_input, cli_output):
        """
        "type"
        (
            (
                "string"
                STRING_TOKEN
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "ranged-string"
                RANGED_STRING_TOKEN_1
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "boolean"
                BOOLEAN
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "int"
                RANGED_INT_TOKEN_1
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "bigger-int"
                RANGED_INT_TOKEN_2
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "negative-int"
                RANGED_INT_TOKEN_3
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "negative-or-positive"
                RANGED_INT_TOKEN_4
                << $cli_input = $1; $cli_output = $2; >>
            )
            |
            (
                "negative-or-zero"
                RANGED_INT_TOKEN_5
                << $cli_input = $1; $cli_output = $2; >>
            )
        )
        """
        print("Input:", cli_input)
        print("Type:", type(cli_output))
        print("Output:", cli_output)

class CmdTest1(unittest.TestCase):

    def test_basic_1(self):
        input_output_err = [
            (
                [""],
                [""],
                [""]
            ),
            (
                ["   "],
                [""],
                [""]
            ),
            (
                ["   ", "   ", "   "],
                [""],
                [""]
            ),
            (
                ["input"],
                ["input: input", "output: output"],
                [""]
            ),
        ]
        loop = asyncio.get_event_loop()
        for inp, out, err in input_output_err:
            with captured_output() as (stdout, stderr):
                loop.run_until_complete(Cmd1.execute_args(*inp))
            stdout = stdout.getvalue().strip().split("\n")
            stderr = stderr.getvalue().strip().split("\n")

            assert out == stdout, "\nstdout: Expected: {}\nstdout: Actual  : {}".format(out, stdout)
            assert err == stderr, "\nstderr: Expected: {}\nstderr: Actual  : {}".format(err, stderr)

    def do_test_type_positive(self, python_type, cli_prefixes, cli_type, cli_types, type_inputs):
        loop = asyncio.get_event_loop()
        cmd = Cmd1(prompt="# ")

        cases = []
        count = 0

        for p in cli_prefixes:
            for c in cli_types:
                for i, o in type_inputs:
                    count += 1
                    inp = " ".join([p, c, i])
                    out = "Input: {}\nType: <class '{}'>\nOutput: {}".format(cli_type, python_type, o).strip()
                    #if count == 100:
                    #    out += "123"
                    err = ""
                    with captured_output() as (stdout, stderr):
                        loop.run_until_complete(cmd.execute_line(inp))

                    stdout = stdout.getvalue().strip()
                    stderr = stderr.getvalue().strip()

                    info = "\n\nFunction: {}".format(inspect.stack()[0][3])
                    info += "\ncli_prefix: {}".format(p)
                    info += "\npython_type: {}".format(python_type)
                    info += "\ncli_type: {}".format(cli_type)
                    info += "\ncli_type input: {}".format(c)
                    info += "\ntype value input: {}".format(i)
                    info += "\ntype value output input: {}".format(o)

                    assert out == stdout, info + "\n\nstdout: Expected: {}\nstdout: Actual  : {}".format(out, stdout)
                    assert err == stderr, info + "\nstderr: Expected: {}\nstderr: Actual  : {}".format(err, stderr)

    def do_test_type_partial(self, python_type, cli_prefixes, cli_type, cli_types, type_inputs):
        loop = asyncio.get_event_loop()
        cmd = Cmd1(prompt="# ")
        cases = []
        count = 0

        for p in cli_prefixes:
            for c in cli_types:
                for i in type_inputs:
                    count += 1
                    inp = " ".join([p, c, i])
                    out = ""
                    err = "Result: partial\nError: Input sequence is not complete"
                    with captured_output() as (stdout, stderr):
                        loop.run_until_complete(cmd.execute_line(inp))

                    stdout = stdout.getvalue().strip()
                    stderr = stderr.getvalue().strip()

                    info = "\n\nFunction: {}".format(inspect.stack()[0][3])
                    info += "\ncli_prefix: {}".format(p)
                    info += "\npython_type: {}".format(python_type)
                    info += "\ncli_type: {}".format(cli_type)
                    info += "\ncli_type input: {}".format(c)
                    info += "\ntype value input: {}".format(i)

                    stdout_info = "\n\nstdout: Expected:\n{}\nstdout: Actual  :\n{}\n".format(out, stdout)
                    stderr_info = "\nstderr: Expected:\n{}\nstderr: Actual  :\n{}\n".format(err, stderr)

                    assert out == stdout, "Failure: stdout mismatch:\n\n" + info + stdout_info + stderr_info
                    assert err == stderr, "Failure: stderr mismatch:\n\n" + info + stdout_info + stderr_info

    def do_test_type_negative(self, python_type, cli_prefixes, cli_type, cli_types, type_inputs):
        loop = asyncio.get_event_loop()
        cmd = Cmd1(prompt="# ")
        cases = []
        count = 0

        for p in cli_prefixes:
            for c in cli_types:
                for i in type_inputs:
                    count += 1
                    inp = " ".join([p, c, i])
                    out = ""
                    err = "Result: failure\nError: Could not match any rule for this sequence"
                    with captured_output() as (stdout, stderr):
                        loop.run_until_complete(cmd.execute_line(inp))

                    stdout = stdout.getvalue().strip()
                    stderr = stderr.getvalue().strip()

                    info = "\n\nFunction: {}".format(inspect.stack()[0][3])
                    info += "\ncli_prefix: {}".format(p)
                    info += "\npython_type: {}".format(python_type)
                    info += "\ncli_type: {}".format(cli_type)
                    info += "\ncli_type input: {}".format(c)
                    info += "\ntype value input: {}".format(i)

                    stdout_info = "\n\nstdout: Expected:\n{}\nstdout: Actual  :\n{}\n".format(out, stdout)
                    stderr_info = "\nstderr: Expected:\n{}\nstderr: Actual  :\n{}\n".format(err, stderr)

                    assert out == stdout, "Failure: stdout mismatch:\n\n" + info + stdout_info + stderr_info
                    assert err == stderr, "Failure: stderr mismatch:\n\n" + info + stdout_info + stderr_info

    def test_type_string_positive(self):
        self.do_test_type_positive(
            "str",
            ["t", "ty", "typ", "type"],
            "string",
            ["s", "st", "str", "string"],
            [
                ('asdfgh', 'asdfgh'),
                ('"asdfgh"', 'asdfgh'),
                ('"type string"', 'type string'),
                (r'"type\nstring"', 'type\nstring'),
                (r'"type\\nstring"', 'type\\nstring'),
                (r'"type\tstring"', 'type\tstring'),
                (r'"type\\tstring"', 'type\\tstring'),
                (r'"type\\string"', 'type\\string'),
                (r'"type\\\\string"', 'type\\\\string'),
                ('""', ''),
                ('12345', '12345'),
                ('"12345"', '12345'),
            ]
        )

    def test_type_string_partial(self):
        self.do_test_type_partial(
            "str",
            ["t", "ty", "typ", "type"],
            "string",
            ["s", "st", "str", "string"],
            ["", " "]
        )

    def test_type_string_negative(self):
        self.do_test_type_negative(
            "str",
            ["t", "ty", "typ", "type"],
            "string",
            ["s", "st", "str", "string"],
            ["a b"]
        )


testcase1 = unittest.TestLoader().loadTestsFromTestCase(CmdTest1)

cli_test = unittest.TestSuite([testcase1])