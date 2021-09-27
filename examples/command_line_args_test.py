import sys
import asyncio

from nessaid_cli.cmd import NessaidCmd
from nessaid_cli.tokens import RangedIntToken, RangedDecimalToken, RangedStringToken, StringToken


class CommandLineCmd(NessaidCmd):
    r"""
    token INT_TOKEN RangedIntToken(0, 100);
    token DECIMAL_TOKEN RangedDecimalToken(-100, 100);
    token RANGED_STR_TOKEN RangedStringToken(1, 20);
    token STR_TOKEN StringToken();
    """

    def __init__(self, **kw):
        super().__init__(**kw)

    def get_token_classes(self):
        return [
            RangedIntToken, RangedDecimalToken, RangedStringToken, StringToken
        ]

    async def do_int(self, i):
        r"""
        "int"
        INT_TOKEN
        << $i = $2; >>
        """
        self.print("Integer:", i)

    def do_decimal(self, d):
        r"""
        "decimal"
        DECIMAL_TOKEN
        << $d = $2; >>
        """
        self.print("Decimal:", d)

    def do_ranged_str(self, s):
        r"""
        "ranged-str"
        RANGED_STR_TOKEN
        << $s = $2; >>
        """
        self.print("Ranged str:", s)

    def do_str(self, s):
        r"""
        "--str"
        STR_TOKEN
        << $s = $2; >>
        """
        self.print("Str:", s)

    async def do_one_to_tem_str(self, l):
        r"""
        << $l = list(); >>
        "-one-to-ten-str"
        (
            STR_TOKEN
            << append($l, $1); >>
        ) * (1: 10)
        """
        self.print("List of Strings:")
        for s in l:
            self.print(s)

    def do_wish(self, name):
        r"""
        "wish"
        STR_TOKEN
        << $name = $2; >>
        """
        self.print("Hi", name)

    def do_user(self, name, age):
        r"""
        << $age = None; >>
        "--user"
        STR_TOKEN
        << $name = $2; >>
        {
            "--age"
            INT_TOKEN
            << $age = $2; >>
        }
        """
        self.print("User:", name)
        if age is not None:
            self.print("Age:", age)

    async def do_set(self, d):
        r"""
        << $d = dict(); >>
        "--info"
        (
            (
                "name"
                STR_TOKEN
                << update($d, $1, $2); >>
            ),
            {
                "age"
                INT_TOKEN
                << update($d, $1, $2); >>
            },
            {
                "decimal"
                DECIMAL_TOKEN
                << update($d, $1, $2); >>
            },
            {
                "nick-name"
                RANGED_STR_TOKEN
                << update($d, $1, $2); >>
            }
        )
        """
        self.print("Info:", d)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        # sys.exit(CommandLineCmd.execute_args(*args))
        sys.exit(CommandLineCmd().exec_args(*args))


"""
############ Commandline run for the Above CLI ##############
E:\>
E:\>python command_line_args_test.py

E:\>python command_line_args_test.py 1
Result: failure
Error: Could not match any rule for this sequence

E:\>python command_line_args_test.py in 1
Integer: 1

E:\>python command_line_args_test.py str aaaaaaa
Result: failure
Error: Could not match any rule for this sequence

E:\>python command_line_args_test.py --str aaaaaaa
Str: aaaaaaa

E:\>python command_line_args_test.py decimal 1
Decimal: 1.0

E:\>python command_line_args_test.py decimal 100
Decimal: 100.0

E:\>python command_line_args_test.py decimal 101
Result: failure
Error: Could not match any rule for this sequence

E:\>python command_line_args_test.py decimal -100
Decimal: -100.0

E:\>python command_line_args_test.py ranged-str 1
Ranged str: 1

E:\>python command_line_args_test.py ranged-str 11111111111111
Ranged str: 11111111111111

E:\>python command_line_args_test.py ranged-str 1111111111111111111111111111
Result: failure
Error: Could not match any rule for this sequence

E:\>python command_line_args_test.py -one-to-ten-str 1
List of Strings:
1

E:\>python command_line_args_test.py -one-to-ten-str 1 2 3 4 5
List of Strings:
1
2
3
4
5

E:\>python command_line_args_test.py -one-to-ten-str 1 2 3 4 5 6 7 8 9 10
List of Strings:
1
2
3
4
5
6
7
8
9
10

E:\>python command_line_args_test.py -one-to-ten-str 1 2 3 4 5 6 7 8 9 10 11
Result: failure
Error: Could not match any rule for this sequence

E:\>python command_line_args_test.py wish Ambu
Hi Ambu

E:\>python command_line_args_test.py w Ami
Hi Ami

E:\>python command_line_args_test.py --u Amjad
User: Amjad

E:\>python command_line_args_test.py --u Amaan --age 5
User: Amaan
Age: 5

E:\>python command_line_args_test.py - Amaan - 5
User: Amaan
Age: 5

E:\>python command_line_args_test.py --info
Result: partial
Error: Input sequence is not complete

E:\>python command_line_args_test.py --info name Amjad
Info: {'name': 'Amjad'}

E:\>python command_line_args_test.py --info name Amjad decimal 3.3
Info: {'name': 'Amjad', 'decimal': 3.3}

E:\>python command_line_args_test.py --info name Amjad decimal 3.3 age 8 nick-name Ambu
Info: {'name': 'Amjad', 'decimal': 3.3, 'age': 8, 'nick-name': 'Ambu'}

E:\>python command_line_args_test.py --info nick-name "Aman M"
Result: partial
Error: Input sequence is not complete

E:\>python command_line_args_test.py --info nick-name "Aman M" na "Muhammed Amaan"
Info: {'nick-name': 'Aman M', 'name': 'Muhammed Amaan'}

E:\>python command_line_args_test.py --info nick-name "Aman M" name "Muhammed Amaan" age 5
Info: {'nick-name': 'Aman M', 'name': 'Muhammed Amaan', 'age': 5}

E:\>python command_line_args_test.py

E:\>echo %ERRORLEVEL%
0

E:\>python command_line_args_test.py 1
Result: failure
Error: Could not match any rule for this sequence

E:\>echo %ERRORLEVEL%
12

E:\>python command_line_args_test.py i 1
Integer: 1

E:\>echo %ERRORLEVEL%
0

E:\>python command_line_args_test.py --info nick-name "Aman M"
Result: partial
Error: Input sequence is not complete

E:\>echo %ERRORLEVEL%
12

E:\>python command_line_args_test.py --info nick-name "Aman M" name "Muhammed Amaan" age 5
Info: {'nick-name': 'Aman M', 'name': 'Muhammed Amaan', 'age': 5}

E:\>echo %ERRORLEVEL%
0
"""
