# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import os
from nessaid_cli.compiler import compile_grammar
from nessaid_cli.cli import NessaidCli

from nessaid_cli.tokens import (
    RangedIntToken,
    RangedStringToken,
    AlternativeStringsToken,
)

class TestCli(NessaidCli):

    def get_token_classes(self):
        """Method to override.
        It should return the list of token classes being used"""
        return [RangedIntToken, RangedStringToken, AlternativeStringsToken]

    def exit(self):
        """This will be called from exit command of the CLI grammar"""
        self.exit_loop()


if __name__ == '__main__':

    grammar_file = os.path.join(os.path.dirname(__file__), "test_input.g")

    with open(grammar_file) as fd:
        inp_str = fd.read()
        grammar_set = compile_grammar(inp_str)

    cli = TestCli(grammar_set, prompt="# ")
    # 'test_grammar' is the grammar to load with the CLI, part of test_input.g
    cli.run('test_grammar')
