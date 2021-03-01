# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys

from nessaid_cli.cmd import NessaidCmd
from nessaid_cli.tokens import (
    RangedIntToken,
    RangedDecimalToken,
    AlternativeStringsToken,
    StringToken,
    RangedStringToken,
    PathToken
)


# For demonstration purpose, many of the properties and capabilities of the
# CLI framework are detailed as examples in following code.

# The following is a definition of a custom token class
# It's derived from the token class to match integer range
class YearToken(RangedIntToken):

    @property
    def helpstring(self):
        return "A year between {} and {}".format(self._start, self._end)


"""
The docstring for the following class will be the global definitions
for the CLI grammar, like token definitions and shared grammars
"""
class testCmd(NessaidCmd):
    """
    token person; # Basic token, matches the string 'person'
    token age; # Basic token, matches the string 'age'
    token age_token RangedIntToken(1, 120);
    # The token 'age_token' is of type RangedIntToken defined in tokens.py
    # Takes the lower and upper limits as arguments

    token integer RangedIntToken(-100, 200, 10);
    # The third argument in above token is maximum number of suggestion.
    # If the number of integers possible from our partial input is
    # less than or equal to it, the CLI will list it as the suggestions.
    # Else CLI will print the helpstring as suggestion

    token RANGED_STRING_TOKEN_1 RangedStringToken(2, 10);
    token decimal RangedDecimalToken(-11.1, 10.6); # Decimal token.
    # min and max range. No numbers will be suggested
    token negative_integer RangedIntToken(-100, -1000);
    token second_integer RangedIntToken(90, 990);
    token birthyear YearToken(1950, 2020); # RangedIntToken extended
    token marital AlternativeStringsToken("married", "unmarried", "separated", "divorced");
    token quit; /* Token used in do_command_to_exit_loop.
        The other 'exit' command option is given as constant for
        demonstration purpose. Refer the methods */

    token str_token StringToken();
    token ranged_str_token RangedStringToken(5, 10);
    token PATH_TOKEN PathToken();

    gent:
        "gent1" | "gent2" | "gent3" | "gent4" | "gent5"
        ;

    grammar1[$var]:
        "grammar1"
        <<$var = "From grammar 1";>>
        ;

    grammar2[$var]:
        "grammar2"
        <<$var = $1;>>
        ;

    main_grammar[]:
        <<$msg = "";>>
        (
            grammar1[$msg]
            |
            grammar2[$msg]
        )
        <<print($msg);>>
        ;
    """
    def do_seq(self, opt, arg):
        """
        "seq"
        {
            "opt1"
            RANGED_STRING_TOKEN_1 << $opt = $2; >>
        }
        (
            RANGED_STRING_TOKEN_1 << $arg = $1; >>
        )
        """
        if opt:
            print("opt:", opt)
        print("arg:", arg)

    def do_main_grammar(self):
        """
        main_grammar
        """
        pass

    def do_path(self, path):
        """
        "path"
        PATH_TOKEN
        <<$path = $2;>>
        """
        print(path)

    def get_token_classes(self):
        """Method to override.
        It should return the list of token classes being used"""
        return [
            YearToken,
            RangedIntToken,
            RangedDecimalToken,
            AlternativeStringsToken,
            StringToken,
            RangedStringToken,
            PathToken
        ]

    # do_ is the default prefix for CLI command handler methods.
    # The doc string is the grammar
    # For the input to match inorder to trigger this function
    def do_person(self, name, year_of_birth, marital_status):
        """
        "person" # Constant string token
        (
            gent
            <<$name = $1;>>
            /* Here $name points to the function parameter name.
            (The Cmd bootstrap code initializes a CLI variable
             for each function parameter and initializes it to "".
             When the grammar matches the function is called with
             the parameters.)
             and $1 points to the first token input ie gent */
        )
        {
            /* This is optional part */
            "birth-year"
            birthyear
            <<
                $year_of_birth = $2;
                # ie $1 is "birth-year" and $2 the year we input
            >>
        }
        {
            "marital-status"
            marital
            <<
                $marital_status = $2;
            >>
        }
        """
        print("=" * 30)
        print("Name:", name)
        if year_of_birth:
            print("Born:", year_of_birth)
        if marital_status:
            print("Marital status:", marital_status)
        print("=" * 30)

    def do_person_another_grammar(self, name, age):
        """
        person # Defined token
        gent <<$name = $2;>>
        age
        age_token <<$age = $4;>>
        """
        print("=" * 30)
        print("{} aged {}".format(name, age))
        print("=" * 30)

    def do_number(self, number):
        """
        "number"
        (
            integer <<$number = $1;>>
            | // Alternative options
            decimal <<$number = $1;>>
        )
        """
        print("=" * 30)
        print("Chosen number: {}".format(number))
        print("=" * 30)

    def do_multiples(self, names, numbers):
        """
        <<
            $names = set();
            $numbers = list();
        >>
        "multiple-test"
        <<print("Showcasing function call support");>>
        (
            gent <<$names = append($names, $1);>>
        ) * 2 # 2 names will be required
        (
            integer <<$number = append($numbers, $1);>>
            | // Alternative options
            decimal <<$number = append($numbers, $1);>>
        ) * (1:3) # Minimum 1 maximum 3.
        {
            /* Optional. Variable count example */
            (
                negative_integer <<$number = append($numbers, $1);>>
            ) * (2:5) # Minimum 2 maximum 5. Overall optional.
        }
        """
        print("=" * 30)
        print("Names:", names)
        print("Numbers:", numbers)
        print("=" * 30)

    # do__exit in NessaidCmd class handles the commands exit | quit | end
    # Let's disable it and override later.
    def do__exit(self):
        pass

    def do_command_to_exit_loop(self):
        """
        "exit" | quit
        """
        self.exit_loop() # Exit call to the base class

    def do_string(self, str1, str2):
        """
        "string-test"
        str_token <<$str1 = $2;>>
        ranged_str_token <<$str2 = $3;>>
        """
        print("=" * 30)
        print("str1:", str1)
        print("str1:", str2)
        print("=" * 30)

    def do_one_more_person(self, name, age, year_of_birth, marital_status):
        """
        "person"
        ranged_str_token <<$name = $2;>>
        "age"
        age_token <<$age = $4;>>
        /*
        Now the following grammar section will give us an option to
        optionally add either marital status or birth year
        or both in any order */
        {
            (
                "birth-year"
                birthyear
                <<
                    $year_of_birth = $2;
                >>
                {
                    "marital-status"
                    marital
                    <<
                        $marital_status = $2;
                    >>
                }
            )
            |
            (
                "marital-status"
                marital
                <<
                    $marital_status = $2;
                >>
                {
                    "birth-year"
                    birthyear
                    <<
                        $year_of_birth = $2;
                    >>
                }
            )
        }
        """
        print("=" * 30)
        print("{} aged {}".format(name, age))
        if year_of_birth:
            print("Born:", year_of_birth)
        if marital_status:
            print("Marital status:", marital_status)
        print("=" * 30)


    def do_test(self):
        """
        "test-string-constant-token" * (1:3)
        """
        print("test")


if __name__ == '__main__':
    cmd = testCmd(prompt="nessaid-cmd # ", show_grammar=True)
    #show_grammar will print the generated grammar specification
    try:
        cmd.loop.run_until_complete(cmd.cmdloop(intro="Starting Nessaid CMD Demo"))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print("Exception in cmdloop:", e)
        sys.exit(1)
    sys.exit(0)
