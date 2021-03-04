# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import ply.lex as lex
import ply.yacc as yacc


class ExtendedString(str):

    def __new__(cls, value, *args, **kwargs):
    	return super(ExtendedString, cls).__new__(cls, value)

    def __init__(self, value, *args, **kwargs):
        self._args = args
        for key, value in kwargs.items():
            setattr(self, key, value)


class TokenString(ExtendedString):

    def __init__(self, value, input=None):
        super().__init__(value, input=value if input is None else input)

    def __add__(self, rhs):
        if isinstance(rhs, TokenString):
            _input = self.input + rhs.input
        elif isinstance(rhs, str):
            _input = self.input + str(rhs)
        else:
            _input = self.input
        return TokenString(str(self) + rhs, input=_input)


class NessaidCliLexerCommon():

    INITIAL_STATE = 'INITIAL'

    states = (
        ('QUOTE','exclusive'),
    )

    tokens = (
        'LPAREN',
        'RPAREN',
        'LBRACE',
        'RBRACE',
        'LBRACKET',
        'RBRACKET',
        'OR',
        'AND',
        'COMMA',
        'COLON',
        'MULTIPLY',
        'SEMICOLON',
        'ASSIGN',
        'IDENTIFIER',
        'INTEGER',
        'FLOAT',
        'DOLLAR_NUMBER_ID',
        'DOLLAR_VAR_ID',
        'NEWLINE',
        'OPEN_QUOTE',
        'QUOTED_CONTENT',
        'CLOSE_QUOTE',
        'ESCAPED_CHAR',
        'ESCAPED_NEWLINE',
        'eof',
    )

    t_LPAREN      = r'\('
    t_RPAREN      = r'\)'
    t_LBRACE      = r'\{'
    t_RBRACE      = r'\}'
    t_LBRACKET    = r'\['
    t_RBRACKET    = r'\]'
    t_COLON       = r':'
    t_SEMICOLON   = r';'

    t_OR          = r'\|'
    t_AND         = r'\&'
    t_COMMA       = r','
    t_ASSIGN      = r'='
    t_MULTIPLY    = r'\*'

    t_IDENTIFIER  = r'[A-Za-z_][-a-zA-Z0-9_]*'
    t_INTEGER     = r'[\+-]?(([0])|(([1-9])([0-9]*)))'
    t_FLOAT       = r'[\+-]?(([0]?)|(([1-9])([0-9]*)))(\.)([0-9]+)'

    t_DOLLAR_NUMBER_ID   = r'[\$][0-9]+'
    t_DOLLAR_VAR_ID      = r'[\$][A-Za-z_][a-zA-Z0-9_]*'

    def t_eof(self, t):
        return None

    t_ignore  = ' \t'
    t_QUOTE_ignore = ""

    def t_NEWLINE(self, t):
        r'(\n|\r\n|\r)+'
        count = self.count_newlines(t.value)
        self.lineno += count

    def t_ESCAPED_CHAR(self, t):
        r'\\([^\n\r])'
        return t

    def t_ESCAPED_NEWLINE(self, t):
        r'\\(\n|\r\n|\r)'
        count = self.count_newlines(t.value)
        self.lineno += count

    def t_QUOTE_QUOTED_CONTENT(self, t):
        r'([^"\n\r\\])+'
        return t

    def t_QUOTE_CLOSE_QUOTE(self, t):
        r'\"'
        self.lexer.begin('INITIAL')
        return t

    t_QUOTE_NEWLINE = t_NEWLINE

    t_QUOTE_ESCAPED_CHAR = t_ESCAPED_CHAR

    t_QUOTE_ESCAPED_NEWLINE = t_ESCAPED_NEWLINE

    def t_error(self, t):
        print("Line: {line} Postion: {position} State: {state}: Illegal character {char}".format(
            line=self.lineno,
            position=self.linepos,
            state=self.state,
            char=t.value[0]
        ))
        t.lexer.skip(1)

    t_QUOTE_error = t_error

    def count_newlines(self, pattern, **kwargs):
        m = pattern
        m.replace("\r\n", "\n")
        m.replace("\r", "\n")
        return m.count("\n")

    @property
    def state(self):
        if self._lex_states:
            return self._lex_states[-1]
        return NessaidCliLexerCommon.INITIAL_STATE

    def enter_state(self, state):
        self._lex_states.append(state)
        self.lexer.begin(state)

    def exit_state(self, state):
        curstate = self._lex_states.pop()
        assert curstate == state
        self.lexer.begin(self._lex_states[-1] if self._lex_states else NessaidCliLexerCommon.INITIAL_STATE)

    def common_OPEN_QUOTE(self, t):
        r'\"'
        self.enter_state('QUOTE')
        return t

    def common_COMMENT(self, t):
        r'(/\*(.|\n)*?\*/)|(//.*)|(\#.*)'
        count = self.count_newlines(t.value)
        self.lineno += count

    @property
    def lexer(self):
        return self._lexer

    @property
    def lineno(self):
        return self._lineno

    @lineno.setter
    def lineno(self, n):
        _incr = n - self._lineno
        self._lineno = int(n)
        self.lexer.lineno += _incr

    @property
    def linepos(self):
        return self._linepos

    @linepos.setter
    def linepos(self, n):
        self._linepos = int(n)

    def __init__(self, lineno=1, linepos=0):
        self._lexer = None
        self._lineno = lineno
        self._linepos = linepos
        self._lex_states = []
        self._lexer = lex.lex(module=self)


class NessaidCliParserCommon():

    def __init__(self):
        self._parser = None
        self._parser = yacc.yacc(module=self, debug=False, write_tables=False)

    @property
    def lexer(self):
        return self._lexer

    @property
    def parser(self):
        return self._parser

    def p_empty(self, t):
        'empty :'
        pass

    def p_quoted_string(self, t):
        'quoted_string : incomplete_quoted_string CLOSE_QUOTE'
        t0 = t[1] + '"'
        t[0] = t0

    def p_incomplete_quoted_string(self, t):
        'incomplete_quoted_string : OPEN_QUOTE quote_body'
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

        t0 = TokenString('"' + t2, '"' + t[2])
        t[0] = t0

    def p_quote_body(self, t):
        """quote_body : quote_text
                      | empty"""
        t1 = t[1]
        if t1 is None:
            t0 = ""
        else:
            t0 = t1
        t0 = TokenString(t0)
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
        t0 = TokenString(t0)
        t[0] = t0

    def p_quote_segment(self, t):
        """quote_segment : QUOTED_CONTENT
                         | ESCAPED_CHAR"""
        t0 = TokenString(t[1])
        t[0] = t0