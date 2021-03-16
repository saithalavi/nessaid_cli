from nessaid_cli.cmd import NessaidCmd
from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer

from nessaid_cli.tokens import (
    StringToken,
    RangedIntToken,
    BooleanToken,
    RangedStringToken,
    AlternativeStringsToken
)

class Cmd1(NessaidCmd):
    """
    token STRING_TOKEN StringToken(), alt AlternativeStringsToken("ab", "a b", "a\\b", "a\\\\\\b", "a\\\\b", "b\t", "c\nc");
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
            AlternativeStringsToken
        ]

    def do_backslash(self, var):
        """
        "back-slash"
        alt
        <<$var = $2;>>
        """
        print("Var:", var)

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


import sys
if __name__ == '__main__':
    cmd = Cmd1(prompt="nessaid-cmd # ", show_grammar=True)
    #show_grammar will print the generated grammar specification
    try:
        cmd.loop.run_until_complete(cmd.cmdloop(intro="Starting Nessaid CMD Demo"))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print("Exception in cmdloop:", e)
        sys.exit(1)
    sys.exit(0)