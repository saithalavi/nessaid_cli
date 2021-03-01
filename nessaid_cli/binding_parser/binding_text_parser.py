# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import ply.lex as lex
import ply.yacc as yacc

from nessaid_cli.lex_yacc_common import NessaidCliLexerCommon
from nessaid_cli.binding_parser.binding_objects import (
    BindingCode,
    NamedVariable,
    NumberedVariable,
    BindingCall,
    FunctionCall,
    AssignmentStatement,
    BindingIntObject,
    BindingStrObject,
    BindingFloatObject)


class NessaidCliBindingLexer(NessaidCliLexerCommon):

    states = (
        ('QUOTE','exclusive'),
    )

    tokens = NessaidCliLexerCommon.tokens + (
        'CALL',
        'OPEN_QUOTE',
        'CLOSE_QUOTE',
        'QUOTED_CONTENT',
        'ESCAPED_CHAR',
        'NEWLINE',
        'ESCAPED_NEWLINE',
        'LEXER_WARNING',
    )

    t_ignore  = ' \t'
    t_QUOTE_ignore = ""

    def t_ignore_COMMENT(self, t):
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    t_ignore_COMMENT.__doc__ = NessaidCliLexerCommon.REGEX_COMMENT

    def t_NEWLINE(self, t):
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    t_NEWLINE.__doc__ = NessaidCliLexerCommon.REGEX_MULTI_NEWLINE

    def t_CALL(self, t):
        "call"
        return t

    def t_INITIAL_OPEN_QUOTE(self, t):
        r'\"'
        self.lexer.begin('QUOTE')
        return t

    def t_QUOTE_QUOTED_CONTENT(self, t):
        r'([^"\n\\])+'
        return t

    def t_QUOTE_ESCAPED_CHAR(self, t):
        r'\\([^\n\r])'
        return t

    def t_QUOTE_ESCAPED_NEWLINE(self, t):
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    t_QUOTE_ESCAPED_NEWLINE.__doc__ = NessaidCliLexerCommon.REGEX_ESCAPED_NEWLINE

    def t_QUOTE_CLOSE_QUOTE(self, t):
        r'\"'
        self.lexer.begin('INITIAL')
        return t

    def t_error(self, t):
        print("INITIAL: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        t.message = "Illegal character {} while scanning code".format(repr(t.value[0]))
        return t

    def t_QUOTE_error(self, t):
        print("QUOTE: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        self.lexer.begin('INITIAL')
        return t

    def __init__(self, filename="", starting_lineno=1):
        self.lexer = lex.lex(module=self)


class ParserException(Exception):

    def __init__(self, filename="", lineno='UNKNOWN', offending_char=None, offernding_token=None, message="", **kwargs):
        self.filename = filename
        self.lineno = lineno
        self.offending_char = offending_char
        self.offernding_token = offernding_token
        self.message = message

    def __str__(self):
        error_info = {}
        if self.offending_char:
            error_info['offending_char'] = self.offending_char
        if self.offernding_token:
            error_info['offernding_token'] = self.offernding_token
        return "{}:{}: {}{}".format(self.filename, self.lineno, self.message, "" if not error_info else " " + str(error_info))


class LexerErrorException(ParserException):
    pass

class NessaidCliBindingParser():

    tokens = NessaidCliBindingLexer.tokens

    def p_binding_content(self, t):
        """grammar_file : empty
                        | content"""
        t1 = t[1]
        t0 = BindingCode(t1) if t1 else BindingCode([])
        """
        print("\n"*5)
        print("binding_content matched:", t0)
        print("\n"*5)
        """
        t[0] = t0

    def p_empty(self, t):
        'empty :'
        pass

    def p_content(self, t):
        """content : block
                   | content block"""
        t[0] = [t[1]] if len(t) == 2 else t[1] + [t[2]]
        #print("content matched:", t[0])

    def p_block(self, t):
        """block : assign_block SEMICOLON
                 | call_block SEMICOLON
                 | function_block SEMICOLON
                 | parser_warning
                 | unused_token"""
        t[0] = t[1]
        #print("Block matched:", t[0])

    def p_assign_block(self, t):
        """assign_block : lhs_block ASSIGN rhs_block"""
        t[0] = AssignmentStatement(t[1], t[3])
        #print("Assign block matched:", t[1], t[2], t[3])

    def p_lhs_block(self, t):
        """lhs_block : DOLLAR_VAR_ID"""
        t[0] = NamedVariable(t[1])
        #print("LHS matched:", t[1])

    def p_rhs_block(self, t):
        """rhs_block : dollar_id
                     | call_block
                     | quoted_string
                     | number
                     | function_block"""
        t[0] = t[1]
        #print("RHS matched:", t[1])

    def p_dollar_id(self, t):
        """dollar_id : dollar_name
                     | dollar_number"""
        t[0] = t[1]
        #print("dollar_id:", t[1])

    def p_dollar_name(self, t):
        'dollar_name : DOLLAR_VAR_ID'
        t[0] = NamedVariable(t[1])

    def p_dollar_number(self, t):
        'dollar_number : DOLLAR_NUMBER_ID'
        t[0] = NumberedVariable(t[1])

    def p_call_block(self, t):
        """call_block : CALL identifier argument_block
                      | CALL identifier"""
        if len(t) == 4:
            t[0] = BindingCall(t[2], t[3])
            #print("Call block matched:", t[2], t[3])
        else:
            t[0] = BindingCall(t[2], [])
            #print("Call block matched:", t[2])

    def p_function_block(self, t):
        """function_block : identifier
                          | identifier argument_block"""
        if len(t) == 2:
            t[0] = FunctionCall(t[1], [])
            #print("Function block matched:", t[1])
        else:
            t[0] = FunctionCall(t[1], t[2])
            #print("Function block matched:", t[1], t[2])

    def p_argument_block(self, t):
        """argument_block : LPAREN optional_argument_list RPAREN"""
        t0 = t[2]
        t[0] = t0

    def p_optional_argument_list(self, t):
        """optional_argument_list : argument_list
                                  | empty"""
        t1 = t[1]
        if t1 is None:
            t0 = []
        else:
            t0 = t1
        t[0] = t0

    def p_argument_list(self, t):
        """argument_list : argument_list COMMA argument
                         | argument"""
        t1 = t[1]
        if len(t) == 2:
            t0 = [t1]
        else:
            t3 = t[3]
            t1.append(t3)
            t0 = t1
        t[0] = t0

    def p_argument(self, t):
        """argument : dollar_id
                    | number
                    | quoted_string
                    | call_block
                    | function_block"""
        t0 = t[1]
        t[0] = t0

    def p_number(self, t):
        """number : integer
                  | float"""
        t0 = t[1]
        t[0] = t0

    def p_integer(self, t):
        """integer : INTEGER"""
        t1 = t[1]
        try:
            t0 = int(t1)
        except Exception:
            t0 = 0
        t[0] = BindingIntObject(t0)

    def p_float(self, t):
        """float : FLOAT"""
        t1 = t[1]
        try:
            t0 = float(t1)
        except Exception:
            t0 = 0.0
        t[0] = BindingFloatObject(t0)

    def p_identifier(self, t):
        """identifier : IDENTIFIER"""
        t[0] = t[1]

    def p_quoted_string(self, t):
        'quoted_string : OPEN_QUOTE quote_body CLOSE_QUOTE'
        t2 = t[2]

        t2s = t2.split("\\\\")

        replace_patterns = {
            '\\"': '"',
            "\\n": "\n",
            "\\r": "\r",
            "\\t": "\t",
        }

        for k, v in replace_patterns.items():
            t2s = [t.replace(k, v) for t in t2s]

        t2 = "\\".join(t2s)

        t[0] = BindingStrObject(t2)

    def p_quote_body(self, t):
        """quote_body : quote_text
                      | empty"""
        t1 = t[1]
        if t1 is None:
            t0 = ""
        else:
            t0 = t1
        t[0] = t0

    def p_quote_text(self, t):
        '''quote_text : quote_text quote_segment
                      | quote_segment'''

        t1 = t[1]
        if len(t) == 2:
            t0 = t1
        else:
            t2 = t[2]
            t0 = t1 + t2
        t[0] = t0

    def p_quote_segment(self, t):
        """quote_segment : QUOTED_CONTENT
                         | ESCAPED_CHAR"""
        t1 = t[1]
        #if t1 in ["\\\\", "\\\""]:
        #    t1 = t1[1:]
        t[0] = t1

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
                        | eof
                        | """
        print("Syntax error (Unused token) at '%s'" % t.value)

    def p_parser_warning(self, t):
        """parser_warning : LEXER_WARNING"""
        print("Warning:", t.value)

    def p_error(self, t):
        if not t:
            return None
        if t.type == 'error':
            if t:
                raise LexerErrorException(
                    filename = self.filename,
                    lineno=t.lineno,
                    offending_char=t.value[0],
                    message=t.message)
            else:
                raise LexerErrorException(
                    filename = self.filename,
                    message="Unknown lexer error"
                )
        else:
            raise ParserException(
                filename = self.filename,
                lineno=t.lineno,
                offernding_token=t.value,
                message="Syntax error"
            )

    def __init__(self, filename="", starting_lineno=1):
        self.filename = filename
        self.starting_lineno = starting_lineno
        self.lexer = NessaidCliBindingLexer(filename=filename, starting_lineno=starting_lineno)
        self.parser = yacc.yacc(module=self, debug=False, write_tables=False)

    def parse(self, input_str):
        try:
            code = self.parser.parse(input_str, lexer=self.lexer.lexer)
            if not isinstance(code, BindingCode):
                errmsg = "Expected {} got {}".format("BindingCode", code if not code else type(code))
                return False, errmsg
            return True, code
        except LexerErrorException as e:
            print("Error:", e)
            return False, str(e)
        except ParserException as e:
            print("Error:", e)
            return False, str(e)


def parse(input_str):
    parser = NessaidCliBindingParser(filename="<SNIPPET>")
    parser.parse(input_str)
