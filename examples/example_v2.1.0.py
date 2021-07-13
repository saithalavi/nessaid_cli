# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys
from nessaid_cli.cmd import NessaidCmd

class TestCmd(NessaidCmd):
    def get_token_classes(self):
        return []

    def do_test(self):
        r"""
        "test"
        """
        print("Normal Function")

    async def do_async(self):
        r"""
        "async"
        """
        print("Async Function")

    def do_blocking_input(self, input_str):
        r"""
        "blocking-input"
        <<
            $input_str = input("cli: ");
            print("Cli Code Input (cli print):", $input_str);
        >>
        """
        inp = self.input("python: ", show_char=False)
        print("Cli Code Input (python print):", input_str)
        print("Python Code Input:", inp)

    async def do_get_input(self, input_str):
        r"""
        "async-input"
        <<
            $input_str = input("cli: ", False);
            print("Cli Code Input (cli print):", $input_str);
        >>
        """
        inp = await self.get_input("python: ", show_char=True)
        print("Cli Code Input (python print):", input_str)
        print("Python Code Input:", inp)

if __name__ == '__main__':
    cmd = TestCmd(prompt="nessaid-cmd # ", show_grammar=True)
    #show_grammar will print the generated grammar specification
    try:
        cmd.loop.run_until_complete(cmd.cmdloop(intro="Starting Nessaid CMD Demo"))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        cmd.error("Exception in cmdloop:", e)
        sys.exit(1)
    sys.exit(0)