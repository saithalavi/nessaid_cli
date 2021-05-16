# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.lex_yacc_common import NessaidCliLexerCommon, NessaidCliParserCommon

from nessaid_cli.binding_parser.binding_objects import (
    BindingCode,
    AssignmentStatement,
    BindingCall,
    FunctionCall,
    BindingStrObject
)


class NessaidCliBindingLexer(NessaidCliLexerCommon):

    tokens = NessaidCliLexerCommon.tokens + (
        'CALL',
        'TRUE',
        'FALSE',
        'NONE',
    )

    t_ignore_COMMENT = NessaidCliLexerCommon.common_COMMENT

    def t_TRUE(self, t):
        "True"
        return t

    def t_FALSE(self, t):
        "False"
        return t

    def t_NONE(self, t):
        "None"
        return t

    def t_CALL(self, t):
        "call"
        return t

    def __init__(self, filename="", starting_lineno=1, starting_linepos=0, stdin=None, stdout=None, stderr=None):
        # Build the lexer
        self._filename = filename
        self._starting_lineno = starting_lineno
        super().__init__(lineno=starting_lineno, linepos=starting_linepos, stdin=stdin, stdout=stdout, stderr=stderr)


class NessaidCliBindingParser(NessaidCliParserCommon):

    tokens = NessaidCliBindingLexer.tokens

    def p_binding_content(self, t):
        """binding_code : empty
                        | content"""
        binding_blocks = t[1]
        binding_code = BindingCode(binding_blocks) if binding_blocks else BindingCode([])
        t[0] = binding_code

    def p_content(self, t):
        """content : block
                   | content block"""
        if len(t) == 2:
            content = [t[1]]
        else:
            content = t[1]
            block = t[2]
            content.append(block)
        t[0] = content

    def p_block(self, t):
        """block : assign_block SEMICOLON
                 | call_block SEMICOLON
                 | function_block SEMICOLON
                 | unused_token"""
        t[0] = t[1]

    def p_assign_block(self, t):
        """assign_block : lhs_block ASSIGN rhs_block"""
        assign_block = AssignmentStatement(t[1], t[3])
        t[0] = assign_block

    def p_lhs_block(self, t):
        """lhs_block : dollar_name"""
        lhs_block = t[1]
        t[0] = lhs_block

    def p_rhs_block(self, t):
        """rhs_block : argument"""
        argument = t[1]
        t[0] = argument

    def p_call_block(self, t):
        """call_block : CALL identifier argument_block"""
        if len(t) == 4:
            call_block = BindingCall(t[2], t[3])
        else:
            call_block = BindingCall(t[2], [])
        t[0] = call_block

    def p_function_block(self, t):
        """function_block : identifier argument_block"""
        if len(t) == 2:
            function_block = FunctionCall(t[1], [])
        else:
            function_block = FunctionCall(t[1], t[2])
        t[0] = function_block

    def p_identifier(self, t):
        """identifier : IDENTIFIER
                      | usable_keywords"""
        identifier = t[1]
        t[0] = identifier

    def p_usable_keywords(self, t):
        """usable_keywords : CALL
                           | TRUE
                           | FALSE
                           | NONE"""
        keyword = t[1]
        t[0] = keyword

    def p_argument_block(self, t):
        """argument_block : LPAREN optional_argument_list RPAREN"""
        argument_list = t[2]
        t[0] = argument_list

    def p_optional_argument_list(self, t):
        """optional_argument_list : argument_list
                                  | empty"""
        argument_list = t[1]
        if argument_list is None:
            argument_list = []
        t[0] = argument_list

    def p_argument_list(self, t):
        """argument_list : argument_list COMMA argument
                         | argument"""
        arguments = t[1]
        if len(t) == 2:
            arguments = [arguments]
        else:
            argument = t[3]
            arguments.append(argument)
        t[0] = arguments

    def p_argument(self, t):
        """argument : dollar_id
                    | call_block
                    | function_block
                    | binding_object"""
        argument = t[1]
        t[0] = argument

    def p_binding_object(self, t):
        """binding_object : number
                          | string_object
                          | boolean_true
                          | boolean_false
                          | none_object"""
        binding_object = t[1]
        t[0] = binding_object

    def p_string_object(self, t):
        """string_object : quoted_string"""
        quoted_str = t[1][1:-1]
        t[0] = BindingStrObject(quoted_str)

    def p_boolean_true(self, t):
        """boolean_true : TRUE"""
        t[0] = True

    def p_boolean_false(self, t):
        """boolean_false : FALSE"""
        t[0] = False

    def p_none_object(self, t):
        """none_object : NONE"""
        t[0] = None

    def p_unused_token(self, t):
        """unused_token : ESCAPED_NEWLINE
                        | NEWLINE
                        | LBRACKET
                        | RBRACKET
                        | OR
                        | AND
                        | COLON
                        | LBRACE
                        | RBRACE
                        | MULTIPLY
                        | ESCAPED_CHAR
                        | SINGLE_BACKSLASH
                        | QUOTED_INCOMPLETE_STR
                        | quoted_split_string
                        | eof"""
        print("Syntax error (Unused token)")
        pass

    def __init__(self, filename="", starting_lineno=1, stdin=None, stdout=None, stderr=None):
        self._filename = filename
        self._starting_lineno = starting_lineno
        self._lexer = NessaidCliBindingLexer(filename=filename, starting_lineno=starting_lineno)
        super().__init__(stdin=stdin, stdout=stdout, stderr=stderr)

    def parse(self, input_str):
        try:
            self.lexer.enter_state(NessaidCliLexerCommon.INITIAL_STATE)
            code = self.parser.parse(input_str, lexer=self.lexer.lexer)
            if not isinstance(code, BindingCode):
                errmsg = "Expected {} got {}".format("BindingCode", code if not code else type(code))
                return False, errmsg
            return True, code
        except Exception as e:
            print("Error:", e)
            return False, str(e)


def parse(input_str):
    parser = NessaidCliBindingParser(filename="<SNIPPET>")
    parser.parse(input_str)
