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

    def do_test(self, m1, m2, o1):
        r"""
        <<$m1 = False;>>
        "m1"
        //<<$m1=True;>>
        "m2"
        <<$m2=True;>>
        {
            "o1"
            <<$o1=True;>>
        }
        """
        print("m1:", m1)
        print("m2:", m2)
        print("o1:", o1)

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