from nessaid_cli.cmd import NessaidCmd

from nessaid_cli.tokens import (
    CliToken,
    StringToken,
    RangedStringToken,
    AlternativeStringsToken,
    RangedIntToken,
    RangedDecimalToken,
    BooleanToken,
    NullTokenValue
)

from nessaid_cli.utils import (
    convert_to_cli_string,
    convert_to_python_string
)


# Example 9 Custom token class: Read with example 9
# This is one of the comparatively complex token implementation. For simpler ones please refer
# nessaid_cli/tokens.py
#
# This token is to match strings which are substrings of the previous token
# The previous token is a StringToken which can match any string. This token on attempted to
# match, will check what the previous token was, and prompt the user with the substrings (separated by commas)
# in the parent string token.

class CustomSubstringToken(CliToken):

    # The parent_index parameter is the index of the parent string in the match sequence
    def __init__(self, name, parent_index, helpstring, cli):
        self._parent_index = parent_index
        super().__init__(name, helpstring=helpstring, cli=cli)

    @property
    def completable(self):
        # So the CLI will prompt the options and do auto completion
        return True

    async def get_options(self, cli, s): # noqa
        matched_values = cli.get_matched_values() # This will fetch the matched tokens it will be: 'token-test' <EXAMPLE_9_PARENT_STRING>
        parent_string = matched_values[self._parent_index]

        # Parent tring will be converted to Python format, to strip quotes and replace with escape characters
        # '"as df"' will be converted to 'as df', 'a\\n' will be converted to 'a\n'
        python_string = convert_to_python_string(parent_string)

        # Now convert the substrings back to CLI format for presenting in CLI
        return [
            convert_to_cli_string(s.strip()) for s in python_string.split(",")
        ]

    async def complete(self, s, cli):
        options = await self.get_options(cli, s)
        # The complete function should return a tuple (n, l) where n is the number of completions and l is the list of completions
        # if argument s is empty, all options will be returned.
        # It can also return (TOO_MANY_COMPLETIONS, []) if n is very large so that the CLI wont clutter, the completion size will come down
        # as the user types and limited options can be printed as suggestions
        return await CliToken.complete_from_multiple(options, s, cli)

    async def match(self, s, cli):
        # match should return either of [MATCH_SUCCESS, MATCH_FAILURE, MATCH_PARTIAL]
        options = await self.get_options(cli, s)
        return await CliToken.match_from_multiple(options, s, cli)

    async def get_value(self, match_string=None, cli=None):
        try:
            n, comp = await self.complete(match_string, cli=cli)
            if n == 1:
                return comp[0]
            elif n > 1:
                if match_string in comp:
                    return match_string
        except:
            pass
        return NullTokenValue

    @property
    def helpstring(self):
        return "A substring of the parent string"

class SimpleCli(NessaidCmd):
    r"""
    # Global grammars and token definitions

    # Token definitions for Example 6: Types
    token STRING_TOKEN StringToken();                       # Matches any string
    token RANGED_STRING_TOKEN RangedStringToken(5, 10);     # Matches any string of length (5-10), inclusive
    token ALT_STRING_TOKEN AlternativeStringsToken("alt1", "alt2", "alt3"); # Matches any one of "alt1", "alt2", "alt3"
    token INT_TOKEN RangedIntToken(0, 100, 20);             # Matches an integer from (0-100), shows 20 suggestions
    token DECIMAL_TOKEN RangedDecimalToken(-100, 100);
    token BOOLEAN_TOKEN BooleanToken();                     # Matche true or False, case insensitive
    # Token definitions for Example 6: Types : End


    # Child grammar definitions for Example 7
    child_grammar_1:
        "child-grammar-1"
        << print("Matched child grammar 1"); >>
        ;

    child_grammar_2[]:
        "child-grammar-2"
        << print("Matched child grammar 2"); >>
        ;

    child_grammar_3[$value1, $value2]:
        "child-grammar-3"
        << $value1 = "Changed by child-grammar-3"; >>
        ;

    child_grammar_4[$value1, $value2]:
        "child-grammar-4"
        << $value1 = $1; >>
        {
            "child-grammar-4"
            << $value2 = $1; >>
        }
        ;
    # Child grammar definitions for Example 7: End

    token EXAMPLE_9_PARENT_STRING StringToken();
    token EXAMPLE_9_SUBSTRING CustomSubstringToken(1); # The argument 1 is needed to locate the parent_string token

    """


    def __init__(self, *args, **kwargs):
        kwargs.update(dict(
            show_grammar=True,          # NessaidCmd is a subclass of nessaid_cli.cli.NessaidCli
                                        # It auto generates the grammar from class and function docstrings
                                        # and feeds to the base class cli object. This flag will make
                                        # the CLI object to print the generated grammar when starting.
            disable_default_hooks=True, # There will be few default commands in base class. We don't want it
            use_base_grammar=False,     # Don't use grammar definitions used by the base class, NessaidCmd
            use_parent_grammar=False,   # Don't use grammar definitions used by the base class
            match_parent_grammar=False, # If we chain CLIs, there's provision to match and switch to parent CLI context
                                        # if the current input fails in the CLI but can be matched in parent. No need here
        ))
        super().__init__(*args, **kwargs)

    def get_token_classes(self):
        # This has to be filled if we are using special token classes
        return [
            StringToken,
            RangedStringToken,
            AlternativeStringsToken,
            RangedIntToken,
            RangedDecimalToken,
            BooleanToken,
            CustomSubstringToken,
        ]

    # Example 1: Constant string tokens
    # Note 1: CLI handlers can be defined as async or non async functions
    # Note 2: CLI handlers are detected by the presense of the designated prefix, by default 'do_', can be changed if needed
    # Note 3: The doc string contains what to be matched for this handler. Once matched, the handler will be called
    # Note 4: It's advised to use raw strings for CLI definition docstrings
    # Note 5: Under the function name we are defining a section of the grammar. The actual grammar
    #         will be auto generated and fed to the CLI code (Handled by nessaid_cli.py)
    # Here we will implement a hook to match either 'quit' or 'exit' and the handler will stop the CLI
    async def do_exit(self):
        r"""
        # Note: This is a comment in CLI grammar expression.
        # Here we are using constant string tokens. The colon after the token value
        # is followed by the helpstring, which will be shown in the prompt
        "exit": "Exit from the CLI session"
        |
        "quit": "Exit from the CLI session"
        """
        self.exit_loop()

    # Example 2: Optional tokens and function calls
    # Note 1: Optional token or block is enclosed in { }
    # Note 2: The CLI hook has an extra parameter optional_chosen. We will see how that can be set from CLI
    # Note 3: Another parameter dummy is added but not used in CLI. By default that will be set to empty string.
    # Note 4: The expressions inside << >> are executed according to their position. The blocks 1 and 2 will be executed
    #         initially. Rest of the blocks will be executed as per their relative positions with tokens
    # Note 5: See the CLI getting matched with the following input
    #       : optional-token mandatory this-is-optional
    #       : o m t
    #       : optional-token mandatory
    #       : o m
    async def do_optional(self, optional_chosen, dummy):
        r"""
        <<
            # Set the initial values of the parameters. param in python code is $param here in CLI code
            $optional_chosen = False;
            # And we are not doing anything with $dummy
        >>

        <<
            # This is to demonstrate multiple execution blocks and function calls. Nothing to do with grammar matching
            print("This is to demonstrate inline calls inside grammar. print is one among few functions calls supported.");
            call print("The above print was just inline in CLI. This print call will reach the CLI object's function");
            # The cli object has a print method defined in utils.py
            print("Multiple args:", 1, "2", 3.0); # Processed inline in CLI
            call print("Multiple args:", 1, "2", 3.0); # Calls CLI objects method
        >>

        "optional-token": "Demonstration of optional token"
        "mandatory": "This token is mandatory"
        {
            "this-is-optional"
            <<  $optional_chosen = True; >>
        }
        """
        if optional_chosen:
            print("Optional token was chosen")
        else:
            print("Optional token was not chosen")
        print("Value of optional_chosen:", type(optional_chosen), optional_chosen)
        print("Value of dummy:", type(dummy), dummy)
        print("dummy:", dummy)

    # Example 3: Optional block
    async def do_optional_block(self, outer_opt, inner_opt):
        r"""
        "optional-block"
        {
            "outer-optional"
            << $outer_opt = $1; >> # $1 matches the value of first token in the (local) sequence
            {
                "inner_optional"
                << $inner_opt = $1; >>
            }
        }
        """
        print("outer_opt:", outer_opt)
        print("inner_opt:", inner_opt)

    # Example 4: Sets
    # Note 1: We can match sets of tokens or blocks.
    # Note 2: Elements in a set can be matched in any order
    # Note 3: Elements of sets are separated by commas
    # Note 4: Elements as a whole should be enclosed in parentheses for mandatory matching or braces for optional
    # Note 5: The below grammar will match a sequence of 1, 2, 3, 4 and 5 in any order, with 3 and 5 being optional
    async def do_set_tokens(self, result_set, result_list, result_dict):
        r"""
        <<
            $result_set = set();
            $result_list = list();
            $result_dict = dict();
        >>
        "set-tokens": "Matches a set of tokens in any order"
        (
            "1" << append($result_set, $1); append($result_list, $1); update($result_dict, $1, $1); >>,
            "2" << append($result_set, $2); append($result_list, $2); update($result_dict, $2, $2); >>,
            {
                "3" << append($result_set, $1); append($result_list, $1); update($result_dict, $1, $1); >>
            },
            "4" << append($result_set, $4); append($result_list, $4); update($result_dict, $4, $4); >>,
            {
                "5" << append($result_set, $1); append($result_list, $1); update($result_dict, $1, $1); >>
            }
        )
        """
        print("Result set:", type(result_set), result_set)
        print("Result list:", type(result_list), result_list)
        print("Result dict:", type(result_dict), result_dict)

    # Example 5: Set of blocks one mandatory and one optional, the set as a whole is oprionsl ie enclosed in {}
    def do_set_block(self, result):
        r"""
        << $result = list(); >>
        "set-blocks"
        { # This is the enclosing braces of the set. Hence the set is optional

            # If we start matching the set, the inner block 2 will be mandatory as that is enclosed in parentheses
            { # Optional set block
                "optional"
                {
                    "set"
                }
                "block"
            } << append($result, $1); >>, # Unlike above example, this $1 matches the sequence above
            (
                "mandatory"
                {
                    "set"
                }
                "block"
            ) << append($result, $2); >>
        }
        # Help yourself matching the above grammar. Bug reports are welcome.
        """
        print("Result:", result)

    # Example 6: Types
    # Note 1: The following type tokens are available by default
    #         string, ranged string, string alternatives, ranged integer, ranged float and boolean
    def do_numbers(self, str_value, ranged_str_value, alt_str_value, int_value, decimal_value, boolean_value):
        r"""
        "types": "Type matching example"
        (
            # STRING_TOKEN, RANGED_STRING_TOKEN etc are token definitions
            # So they have to be defined in global grammar, so put the definitions in class docstring
            {
                "string"
                STRING_TOKEN
                << $str_value = $2; >>
            },
            {
                "ranged-string"
                RANGED_STRING_TOKEN
                << $ranged_str_value = $2; >>
            },
            {
                "string-alternatives"
                ALT_STRING_TOKEN
                << $alt_str_value = $2; >>
            },
            {
                "int"
                INT_TOKEN
                << $int_value = $2; >>
            },
            {
                "decimal"
                DECIMAL_TOKEN
                << $decimal_value = $2; >>
            },
            {
                "boolean"
                BOOLEAN_TOKEN
                << $boolean_value = $2; >>
            }
        )
        """
        print(f"str_value: type: {type(str_value)}: value: {str_value}")
        print(f"ranged_str_value: type: {type(ranged_str_value)}: value: {ranged_str_value}")
        print(f"alt_str_value: type: {type(alt_str_value)}: value: {alt_str_value}")
        print(f"int_value: type: {type(int_value)}: value: {int_value}")
        print(f"decimal_value: type: {type(decimal_value)}: value: {decimal_value}")
        print(f"boolean_value: type: {type(boolean_value)}: value: {boolean_value}")

    # Example 7: Chaining grammars and passing parameters
    async def do_grammar_chain(self, value1, value2, value3):
        r"""
        <<
            $value2 = 0;
            $value3 = None;
        >>
        # Note: The child grammars should be present globally, ie. in class docstring
        "grammar-chain"
        (
            child_grammar_1
            |
            child_grammar_2[]
            |
            child_grammar_3[$value1, $value2]
            |
            child_grammar_4[$value2, $value3]
        )
        """
        print("value1:", type(value1), value1)
        print("value2:", type(value2), value2)
        print("value3:", type(value3), value3)

    # Example 8: Match multiple times, Not much practical use
    def do_multiple(self, result):
        r"""
        << $result = list(); >>
        {"multiple"
        (
            "match-twice" << append($result, $1); >>
        ) * 2}

        (
            "match-one-to-three-times"
            << append($result, $1); >>
        )* (1:3)

        """
        print("Result:", result)


    # Example 9: Defining a custom token
    """
    In this example we will define a custom token with auto completion and suggestion. See the CLI interaction below
    The command we implement will have 3 tokens
    token 1: initial command token - 'token-test'
    token 2: StringToken - any string
    token 3: Our custom token. It will match any substring from token 2 separated by comma, token 2 can be put inside quotes so that
             spaces can be included in it
    """
    def do_custom_token(self, parent_string, sub_string):
        r"""
        "token-test"
        EXAMPLE_9_PARENT_STRING
        << $parent_string = $2; >>
        EXAMPLE_9_SUBSTRING
        << $sub_string = $3; >>
        """
        print("parent_string:", parent_string)
        print("sub_string:", sub_string)

    # Example 10: Gathering input
    # Input can be done with async or non-async functions, get_input and input respectively
    # Input can be gathered with masking echo, pass show_char argument as False
    # Input can be triggered either from CLI grammar or python code.
    # Below example shows all combinations
    async def do_input(self, async_inp, show_char, input_str):
        r"""
        << $show_char = True; >>
        (
            "input"
            {
                {
                    "async"
                    << $async_inp = True; >>
                },
                {
                    "mask-input"
                    << $show_char = False; >>
                }
            }
        )
        <<
            $input_str = input("cli: ", $show_char);
            print("Cli Code Input (cli print):", $input_str);
        >>
        """
        if async_inp:
            inp = await self.get_input("python: ", show_char=show_char)
        else:
            inp = self.input("python: ", show_char=show_char)
        print("Cli Code Input (python print):", input_str)
        print("Python Code Input:", inp)

        """
        Here's the CLI interaction for example 10

        simple-cli # inp
        cli: cli
        Cli Code Input (cli print): cli
        python: python
        Cli Code Input (python print): cli
        Python Code Input: python
        simple-cli #
        simple-cli # inp mas
        cli: ***
        Cli Code Input (cli print): cli
        python: ******
        Cli Code Input (python print): cli
        Python Code Input: python
        simple-cli #
        simple-cli # inp as
        cli: cli
        Cli Code Input (cli print): cli
        python: python
        Cli Code Input (python print): cli
        Python Code Input: python
        simple-cli # inp as mask
        cli: ***
        Cli Code Input (cli print): cli
        python: ******
        Cli Code Input (python print): cli
        Python Code Input: python
        simple-cli #
        """


"""
Example 9 CLI interaction
=========================

simple-cli #
simple-cli # to<TAB>

token-test :    token-test

simple-cli # to <TAB>

 :    Any string

simple-cli # to asdf <TAB>

asdf :    A substring of the parent string

simple-cli # to asdf a<ENTER>
parent_string: asdf
sub_string: asdf
simple-cli #
simple-cli # token "asdf, 123, asdf 123, 1 2 3"<TAB>

"1 2 3"    :    A substring of the parent string
"asdf 123" :    A substring of the parent string
123        :    A substring of the parent string
asdf       :    A substring of the parent string

simple-cli # token "asdf, 123, asdf 123, 1 2 3" 1<ENTER>
parent_string: asdf, 123, asdf 123, 1 2 3
sub_string: 123
simple-cli # token "asdf, 123, asdf 123, 1 2 3" as<ENTER>
parent_string: asdf, 123, asdf 123, 1 2 3
sub_string: asdf
simple-cli # token "asdf, 123, asdf 123, 1 2 3" "<TAB>

"1 2 3"    :    A substring of the parent string
"asdf 123" :    A substring of the parent string

simple-cli # token "asdf, 123, asdf 123, 1 2 3" "1<ENTER>
parent_string: asdf, 123, asdf 123, 1 2 3
sub_string: 111 222
simple-cli #
simple-cli # token "asdf, 123, asdf 123, 1 2 3" "a<TAB>

"asdf 123" :    A substring of the parent string

simple-cli # token "asdf, 123, asdf 123, 1 2 3" "asdf 123"<ENTER>
parent_string: asdf, 123, asdf 123, 1 2 3
sub_string: asdf 123
simple-cli #
simple-cli #
simple-cli # to<TAB>

token-test :    token-test

simple-cli # to "asdf\n,123 123,a\tb"<TAB>

 :    Any string

simple-cli # to "asdf\n,123 123,a\tb" <TAB>

"123 123" :    A substring of the parent string
"a\tb"    :    A substring of the parent string
asdf      :    A substring of the parent string

simple-cli # to "asdf\n,123 123,a\tb" a<ENTER>
parent_string: asdf
,123 123,a      b
sub_string: asdf
simple-cli # to "asdf\n,123 123,a\tb" "<TAB>

"123 123" :    A substring of the parent string
"a\tb"    :    A substring of the parent string

simple-cli # to "asdf\n,123 123,a\tb" "1<ENTER>
parent_string: asdf
,123 123,a      b
sub_string: "123 123"
simple-cli # to "asdf\n,123 123,a\tb" "1<TAB><TAB>

"123 123" :    A substring of the parent string

simple-cli # to "asdf\n,123 123,a\tb" "123 123"<ENTER>
parent_string: asdf
,123 123,a      b
sub_string: "123 123"
simple-cli # to "asdf\n,123 123,a\tb" "<TAB>

"123 123" :    A substring of the parent string
"a\tb"    :    A substring of the parent string

simple-cli # to "asdf\n,123 123,a\tb" "a\tb"<ENTER>
parent_string: asdf
,123 123,a      b
sub_string: "a  b"
simple-cli #
"""


cli_intro = """
Introduction to nessaid-cli

Use <TAB> to list available commands

a partial input following a <TAB> will complete the token if only one expansion is possible, else it
will list all possible expansions

If we have a token 'test-token' and we don't have any other token starting with t, typing 't' ot 'te' is enough to
match the token

Supports following basic line editing options

arrow keys
history and search CTRL+R for backward lookup, CTRL+S for forward lookup PAGE_UP for first history entry page down for last

HOME or ATRL+A for beginning of line
END or CTRL+E for end of line

INSERT for toggling INSERT/REPLACE

CTRL+C for canceling current input
CTRL+D to exit CLI

"""

if __name__ == '__main__':
    SimpleCli(prompt="simple-cli # ").run(intro=cli_intro)