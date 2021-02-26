# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys
from nessaid_cli.compiler import compile
from nessaid_cli.cli import NessaidCli

from nessaid_cli.tokens import (
    RangedIntToken,
    RangedStringToken
)

class TestCli(NessaidCli):

    def get_token_classes(self):
        """Method to override.
        It should return the list of token classes being used"""
        return [RangedIntToken, RangedStringToken]

    def print(self, *args):
        print("External function:", *args)

    def exit(self):
        """This will be called from exit command of the CLI grammar"""
        self.exit_loop()


if __name__ == '__main__':
    with open("test_input.g") as fd:
        inp_str = fd.read()
        grammar_set = compile(inp_str)

    cli = TestCli(grammar_set, prompt="# ")
    try:
        cli.loop.run_until_complete(cli.cmdloop('test_grammar', intro="Starting Nessaid CLI Demo"))
        # 'test_grammar' above is the grammar to load with the CLI, part of test_input.g
    except KeyboardInterrupt:
        sys.exit(0)
    sys.exit(1)