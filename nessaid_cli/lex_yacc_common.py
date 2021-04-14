# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import ply.lex as lex
import ply.yacc as yacc

from nessaid_cli.utils import StdStreamsHolder, ExtendedString


class CliLexerError(Exception):
    pass

class CliSyntaxError(Exception):
    pass


class DollarNumber(ExtendedString):

    def __init__(self, value):
        super().__init__(value)


class DollarVariable(ExtendedString):

    def __init__(self, value):
        super().__init__(value)


class NessaidCliLexerCommon(StdStreamsHolder):

    INITIAL_STATE = 'INITIAL'

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
        'ESCAPED_CHAR',
        'SINGLE_BACKSLASH',
        'ESCAPED_NEWLINE',
        'QUOTED_STR',
        'QUOTED_INCOMPLETE_STR',
        'HEX_NUMBER',
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
    t_QUOTED_STR  = r'(")(([^"\n\r\t\\\0])|((\\\\)|(\\)(0|n|r|t|b|v|a|")))*(")'
    t_HEX_NUMBER  = r'(0)(x|X)([a-fA-F0-9]+)'

    t_DOLLAR_NUMBER_ID   = r'[\$][0-9]+'
    t_DOLLAR_VAR_ID      = r'[\$][A-Za-z_][a-zA-Z0-9_]*'

    def t_eof(self, t):
        return None

    t_ignore  = ' \t'

    def t_NEWLINE(self, t):
        r'(\n|\r\n|\r)+'
        self.update_counters(t)

    def t_ESCAPED_CHAR(self, t):
        r'\\([^\n\r])'
        return t

    def t_ESCAPED_NEWLINE(self, t):
        r'\\(\n|\r\n|\r)'
        self.update_counters(t)

    def t_error(self, t):
        self.update_counters(t)

        def _repr(t):
            v = t
            if v:
                v.replace('\n', "'\\n'")
                v.replace('\t', "'\\t'")
            return v

        err_msg = "Line: {line} Postion: {position} State: {state}: Illegal character {char}".format(
            line=self.lineno,
            position=self.linepos,
            state=self.state,
            char=_repr(t.value[0])
        )
        self.error(err_msg)
        raise CliLexerError(err_msg)

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

    def common_COMMENT(self, t):
        r'(/\*(.|\n)*?\*/)|(//.*)|(\#.*)'
        self.update_counters(t)

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
        try:
            if self.lexer:
                return self.lexer.lexpos - self._size_till_last_newline
        except Exception:
            pass
        return 0

    def update_counters(self, t):
        count = self.count_newlines(t.value)
        self.lineno += count
        if count:
            self._size_till_last_newline = t.lexpos + max(t.value.rfind("\r"), t.value.rfind("\n")) + 1

    @property
    def size_till_last_newline(self):
        return self._size_till_last_newline

    def __init__(self, lineno=1, linepos=0, stdin=None, stdout=None, stderr=None):

        self.init_streams(stdin=stdin, stdout=stdout, stderr=stderr)

        self._lexer = None
        self._lineno = lineno
        self._size_till_last_newline = 0
        self._lex_states = []
        self._lexer = lex.lex(module=self)


class NessaidCliParserCommon(StdStreamsHolder):

    def __init__(self, stdin=None, stdout=None, stderr=None):

        self.init_streams(stdin=stdin, stdout=stdout, stderr=stderr)

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
        """quoted_string : QUOTED_STR"""
        quoted_string = t[1]
        t[0] = quoted_string

    def p_quoted_split_string(self, t):
        """quoted_split_string : quoted_split_string QUOTED_STR
                               | QUOTED_STR"""
        quoted_string = t[1]
        if len(t) == 3:
            quoted_string_to_add = t[2]
            quoted_string = quoted_string + quoted_string_to_add

        t[0] = quoted_string

    def p_number(self, t):
        """number : integer
                  | float"""
        number = t[1]
        t[0] = number

    def p_integer(self, t):
        """integer : INTEGER
                   | HEX_NUMBER"""
        int_str =  t[1]
        integer = int(int_str)
        t[0] = integer

    def p_float(self, t):
        """float : FLOAT"""
        float_str = t[1]
        float_val = float(float_str)
        t[0] = float_val

    def p_dollar_id(self, t):
        """dollar_id : dollar_name
                     | dollar_number"""
        dollar_id = t[1]
        t[0] = dollar_id

    def p_dollar_name(self, t):
        'dollar_name : DOLLAR_VAR_ID'
        dollar_name = t[1]
        t[0] = DollarVariable(dollar_name)

    def p_dollar_number(self, t):
        'dollar_number : DOLLAR_NUMBER_ID'
        dollar_number = t[1]
        t[0] = DollarNumber(dollar_number)

    def p_error(self, t):

        def _repr(t):
            v = t.value if t is not None and hasattr(t, 'value') else t
            if v:
                v.replace('\n', "'\\n'")
                v.replace('\t', "'\\t'")
            return v

        err_msg = "Line: {line} Postion: {position} State: {state}: Syntax Error at: {token}".format(
            line=self.lexer.lineno,
            position=self.lexer.linepos,
            state=self.lexer.state,
            token=_repr(t))

        self.error(err_msg)
        raise CliSyntaxError(err_msg)