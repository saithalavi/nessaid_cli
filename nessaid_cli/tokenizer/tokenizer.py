# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import ply.lex as lex
import ply.yacc as yacc


class NessaidCliTokenizerLexer():

    states = (
        ('QUOTE','exclusive'),
    )

    tokens = (
        'COLON',
        'SEMICOLON',
        'LPAREN',
        'RPAREN',
        'LBRACE',
        'RBRACE',
        'LBRACKET',
        'RBRACKET',
        'IDENTIFIER',
        'TEXT',
        'OR',
        'AND',
        'OPEN_QUOTE',
        'CLOSE_QUOTE',
        'QUOTED_CONTENT',
        'ESCAPED_CHAR',
        'NEWLINE',
        'ESCAPED_NEWLINE',
        'eof'
    )

    t_LPAREN      = r'\('
    t_RPAREN      = r'\)'
    t_LBRACE      = r'\{'
    t_RBRACE      = r'\}'
    t_LBRACKET    = r'\['
    t_RBRACKET    = r'\]'
    t_IDENTIFIER  = r'[A-Za-z_][-a-zA-Z0-9]*'

    t_OR          = r'\|'
    t_AND         = r'\&'
    t_COLON       = r':'
    t_SEMICOLON   = r';'
    t_NEWLINE     = r'(\n|\r\n|\r)+'

    t_ignore  = ' \t'
    t_QUOTE_ignore = ""


    def t_INITIAL_OPEN_QUOTE(self, t):
        r'\"'
        self.lexer.begin('QUOTE')
        """
        print("\n"*2)
        print("t:", t)
        print("t.value:", t.value)
        print("\n"*2)
        """
        return t

    def t_TEXT(self, t):
        r'([^"\n\\ \t])+'
        #print("\n"*2)
        #print("t:", t)
        #print("t.value:", t.value)
        #print("\n"*2)
        return t

    def t_QUOTE_QUOTED_CONTENT(self, t):
        r'([^"\n\\])+'
        #print("\n"*2)
        #print("t:", t)
        #print("t.value:", t.value)
        #print("\n"*2)
        return t

    def t_QUOTE_ESCAPED_CHAR(self, t):
        r'\\([^\n\r])'
        #print("\n"*2)
        #print("t:", t)
        #print("t.value:", t.value)
        #print("\n"*2)
        return t

    def t_QUOTE_ESCAPED_NEWLINE(self, t):
        r'\\(\n|\r\n|\r)+'
        #print("\n"*2)
        #print("t:", t)
        #print("t.value:", t.value)
        #print("\n"*2)
        pass

    def t_QUOTE_CLOSE_QUOTE(self, t):
        r'\"'
        self.lexer.begin('INITIAL')
        """
        print("\n"*2)
        print("t:", t)
        print("t.value:", t.value)
        print("\n"*2)
        """
        return t

    def t_eof(self, t):
        return None

    def t_error(self, t):
        print("INITIAL: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def t_QUOTE_error(self, t):
        #print(t.value)
        print("QUOTE: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        self.lexer.begin('INITIAL')

    def __init__(self, filter_special_chars=None):
        self.adjust_token_rules(filter_special_chars)
        self.lexer = lex.lex(module=self)

    def adjust_token_rules(self, filter_chars):
        pass


class NessaidCliTokenizer():

    tokens = NessaidCliTokenizerLexer.tokens

    def __init__(self):
        self.lexer = NessaidCliTokenizerLexer()
        self.parser = yacc.yacc(module=self, debug=False, write_tables=False)

    def parse(self, input_str):
        self.lexer.lexer.begin('INITIAL')
        return self.parser.parse(input_str, lexer=self.lexer.lexer)

    def p_line_content(self, t):
        """line_content : input empty
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
                        | OR
                        | RBRACE
                        | RBRACKET
                        | RPAREN
                        | SEMICOLON"""
        print("Syntax error (Unused token) at '%s'" % t.value)
        t[0] = []

    def p_input(self, t):
        'input : line'
        t0 = t[1]
        t[0] = t0

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
        """segment : TEXT
                   | quoted_string
                   | incomplete_quoted_string"""
        t1 = t[1]
        t[0] = t1

    def p_quoted_string(self, t):
        'quoted_string : incomplete_quoted_string CLOSE_QUOTE'
        t[0] = t[1] + '"'

    def p_incomplete_quoted_string(self, t):
        'incomplete_quoted_string : OPEN_QUOTE quote_body'
        t2 = t[2]

        replace_patterns = {
            "\\n": "\n",
            "\\r": "\r",
            "\\t": "\t",
        }

        for k, v in replace_patterns.items():
            t2 = t2.replace(k, v)

        t[0] = '"' + t2

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
        if t1 in ["\\\\", "\\\""]:
            t1 = t1[1:]
        t[0] = t1

    def p_empty(self, t):
        'empty :'
        pass

def tokenize(input_str):
    parser = NessaidCliTokenizer()
    return parser.parse(input_str)

if __name__ == '__main__':
    while True:
        line = input("Test: ")
        tokens = tokenize(line)
        print("Tokens:", tokens)