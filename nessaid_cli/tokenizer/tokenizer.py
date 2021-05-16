# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import traceback

import ply.lex as lex
import ply.yacc as yacc

from nessaid_cli.utils import StdStreamsHolder, ExtendedString


class TokenizerIllegalCharError(Exception):

    def __init__(self, msg, token=None):
        self.token = token
        super().__init__(msg)


class TokenizerSyntaxError(Exception):

    def __init__(self, msg, token=None):
        self.token = token
        super().__init__(msg)


class TokenizerException(Exception):

    def __init__(self, msg, token=None):
        self.token = token
        super().__init__(msg)


class TokenInputString(ExtendedString):

    def __init__(self, value, lexpos, lexlen, quoted=False, quote_incomplete=False):
        if quote_incomplete is True:
            quoted = True
        super().__init__(value, lexpos=lexpos, lexlen=lexlen, quoted=quoted, quote_incomplete=quote_incomplete)


class NessaidCliTokenizerLexer(StdStreamsHolder):

    tokens = (
        'TEXT',
        'QUOTED_STR',
        'QUOTED_INCOMPLETE_STR',
    )

    def t_TEXT(self, t):
        r'([^"\n\\ \t])+'
        t.value = TokenInputString(t.value, t.lexpos, len(t.value))
        return t

    def t_QUOTED_STR(self, t):
        r'(")(([^"\n\r\t\\\0])|((\\\\)|(\\)(0|n|r|t|b|v|a|")))*(")'
        t.value = TokenInputString(t.value, t.lexpos, len(t.value), quoted=True)
        return t

    def t_QUOTED_INCOMPLETE_STR(self, t):
        r'(")(([^"\n\r\t\\\0])|((\\\\)|(\\)(0|n|r|t|b|v|a|")))*(\\)?'
        t.value = TokenInputString(t.value, t.lexpos, len(t.value), quote_incomplete=True)
        return t

    @property
    def lexer(self):
        return self._lexer

    def __init__(self, stdin=None, stdout=None, stderr=None):
        self._lexer = None
        self.init_streams(stdin=stdin, stdout=stdout, stderr=stderr)
        self._lexer = lex.lex(module=self)

    t_ignore  = ' \t'

    def t_error(self, t):
        raise TokenizerIllegalCharError("Illegal character: '{}'".format(t.value[0]), token=t.value[0])


class NessaidCliTokenizer(StdStreamsHolder):

    tokens = NessaidCliTokenizerLexer.tokens

    @property
    def lexer(self):
        return self._lexer

    @property
    def parser(self):
        return self._parser

    def __init__(self, stdin=None, stdout=None, stderr=None):
        self._lexer = None
        self._parser = None
        self.init_streams(stdin=stdin, stdout=stdout, stderr=stderr)

        self._lexer = NessaidCliTokenizerLexer(stdin=stdin, stdout=stdout, stderr=stderr)
        self._parser = yacc.yacc(module=self, debug=False, write_tables=False)

    def parse(self, input_str):
        try:
            return self.parser.parse(input_str, lexer=self.lexer.lexer)
        except TokenizerIllegalCharError as e:
            error_msg = "Illegal character error while tokenizing." + " Token: {}".format(e.token) if e.token else ""
            raise TokenizerException(error_msg, token=e.token)
        except TokenizerSyntaxError as e:
            error_msg = "Syntax error while tokenizing." + " Token: {}".format(e.token) if e.token else ""
            raise TokenizerException(error_msg, token=e.token)
        except Exception as e:
            error_msg = "Exception while tokenizing: {}".format(str(e)) + " Token: {}".format(e.token) if e.token else ""
            return e

    def p_line_content(self, t):
        """line_content : line empty"""
        line = t[1]
        t[0] = line

    def p_line(self, t):
        """line : line segment
                | empty"""
        line = t[1]
        if line is None:
            line = []
        else:
            segment = t[2]
            line.append(segment)
        t[0] = line

    def p_segment(self, t):
        """segment : text
                   | quoted_string
                   | incomplete_quoted_string"""
        segment = t[1]
        t[0] = segment

    def p_quoted_string(self, t):
        'quoted_string : QUOTED_STR'
        quoted_string = t[1]
        t[0] = quoted_string

    def p_incomplete_quoted_string(self, t):
        'incomplete_quoted_string : QUOTED_INCOMPLETE_STR'
        quoted_string = t[1]
        t[0] = quoted_string

    def p_text(self, t):
        'text : TEXT'
        text = t[1]
        t[0] = text

    def p_empty(self, t):
        'empty :'
        pass

    def p_error(self, t):
        raise Exception("Error parsing input line")


def tokenize(input_str):
    parser = NessaidCliTokenizer()
    tokens = []
    try:
        tokens = parser.parse(input_str)
    except TokenizerException as e:
        parser.error("Failed to tokenize input:", e)
    except Exception as e:
        parser.error("Exception tokenizing input: {}\nException: {}: {}".format(input_str, type(e), e))
    return tokens


def test_main():
    while True:
        try:
            line = input("Test: ")
            tokens = tokenize(line)
            print("Line:", line)
            print("Tokens:", tokens)
            print("Tokens Inputs:", [t.value for t in tokens])
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Exception:", type(e), e)


if __name__ == '__main__':
    test_main()