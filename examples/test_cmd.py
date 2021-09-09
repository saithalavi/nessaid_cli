# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.cmd import NessaidCmd

from nessaid_cli.tokens import (
    RangedIntToken,
    RangedStringToken
)

class TestCmd(NessaidCmd):
    r"""
    token TEST_NUMBER RangedIntToken(1, 100); // Token to match integer between 1 and 100
    token STRING_TOKEN RangedStringToken(5, 10); // Token to match a string of length 5 to 10
    """

    def get_token_classes(self):
        """Method to override.
        It should return the list of token classes being used"""
        return [RangedIntToken, RangedStringToken]

    def do_command1(self, number):
        r"""
        "command\n1"
        TEST_NUMBER
        <<
            $number = $2;
        >>
        """

        """
        The Cmd framework here does the following

        1. Generate a named grammar corresponding to the do_command1 method
            with the method's docstring as grammar body.
        2. The grammar body will have local variables generated for each parameter
            of the method. ie here a local variable $number will be available for the
            grammar so that we can assign the input number to it in the action.
            If we don't assign anything the value of the variable will be ""
        3. Generate a master grammar which is the alternatives of the method grammars
            ie. Like

            master_grammar:
                do_command1
                |
                do_command2
                |
                do_command3
                ;

        4. When the grammar of a method matches the method will be called with the
            arguments.
        """

        # Now that the grammar matched, the function will be called with the arguments
        # we prepared. Process them in the function
        print("Incoming variable is not there. The feature is not yet ready for Cmd. This is the python print method")
        print("Input number is:", number)

    def do_command2(self, string):
        r"""
        "command2"
        STRING_TOKEN
        <<
            $string = $2;
            print("Inline print: Input number:", $2);
            call print("Input number:", $2);
        >>
        """
        print("Input str is:", string)

    def do_command3(self, string, number, numbers):
        r"""
        <<
            $numbers = list();
        >>

        "command3"
        STRING_TOKEN
        <<
            $string = $2;
        >>
        TEST_NUMBER
        <<
            $number = $3;
        >>
        # Now we may input an optional list with minimum 1 and maximum 3 integers
        {
            (
                TEST_NUMBER << $numbers = append($numbers, $1);>>
            ) * (1:3)
        }
        """
        print("Input str is:", string)
        print("Input number is:", number)
        print("Input list is:", numbers)


if __name__ == '__main__':
    cmd = TestCmd(prompt="nessaid-cmd # ", show_grammar=True)
    #show_grammar will print the generated grammar specification
    cmd.run(intro="Starting Nessaid CMD Demo")