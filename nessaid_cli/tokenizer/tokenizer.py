# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.lex_yacc_common import NessaidCliLexerCommon, NessaidCliParserCommon, TokenString


class NessaidCliTokenizerLexer(NessaidCliLexerCommon):

    tokens = NessaidCliLexerCommon.tokens + (
        'TEXT',
    )

    def t_TEXT(self, t):
        r'([^"\n\\ \t])+'
        return t

    t_INITIAL_OPEN_QUOTE = NessaidCliLexerCommon.common_OPEN_QUOTE

    def __init__(self, filter_special_chars=None):
        self.adjust_token_rules(filter_special_chars)
        super().__init__()

    def adjust_token_rules(self, filter_chars):
        pass


class NessaidCliTokenizer(NessaidCliParserCommon):

    tokens = NessaidCliTokenizerLexer.tokens

    def __init__(self):
        self._lexer = NessaidCliTokenizerLexer()
        super().__init__()

    def parse(self, input_str):
        self.lexer.enter_state(NessaidCliTokenizerLexer.INITIAL_STATE)
        return self.parser.parse(input_str, lexer=self.lexer.lexer)

    def p_line_content(self, t):
        """line_content : line empty
                        | unused_token"""
        t0 = t[1]
        t[0] = t0

    def p_error(self, t):
        if t:
            print("Syntax error at '%s'" % t.value)
        t[0] = []

    def p_unused_token(self, t):
        """unused_token : ESCAPED_NEWLINE
                        | NEWLINE
                        | AND
                        | eof
                        | COLON
                        | IDENTIFIER
                        | LBRACE
                        | LBRACKET
                        | LPAREN
                        | ASSIGN
                        | COMMA
                        | FLOAT
                        | INTEGER
                        | MULTIPLY
                        | DOLLAR_VAR_ID
                        | DOLLAR_NUMBER_ID
                        | OR
                        | RBRACE
                        | RBRACKET
                        | RPAREN
                        | SEMICOLON"""
        print("Syntax error (Unused token) at '%s'" % t.value)
        t[0] = []

    def p_line(self, t):
        """line : line segment
                | empty"""
        t1 = t[1]
        if t1 is None:
            t0 = []
        else:
            t2 = t[2]
            t0 = t1 + [t2]
        t[0] = t0

    def p_segment(self, t):
        """segment : text
                   | quoted_string
                   | incomplete_quoted_string"""
        t1 = t[1]
        t[0] = t1

    def p_text(self, t):
        'text : TEXT'
        t1 = t[1]
        t[0] = TokenString(t1)

def tokenize(input_str):
    parser = NessaidCliTokenizer()
    return parser.parse(input_str)


def main():
    while True:
        try:
            line = input("Test: ")
            tokens = tokenize(line)
            print("Line:", line)
            print("Tokens:", tokens)
            print("Tokens Inputs:", [t.input for t in tokens])
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Exception:", type(e), e)


def token_info():

    while True:
        try:
            line = input("Test: ")
            tokens = tokenize(line)
            print("Line:", line)
            print("Line: repr:", repr(line))
            print("Tokens:", tokens)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Exception:", type(e), e)


if __name__ == '__main__':
    main()