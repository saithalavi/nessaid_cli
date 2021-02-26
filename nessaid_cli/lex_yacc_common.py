# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

class NessaidCliLexerCommon():

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

    REGEX_NEWLINE = r'\r\n|\n|\r'
    REGEX_MULTI_NEWLINE = r'(\n|\r\n|\r)+'
    REGEX_ESCAPED_NEWLINE = r'\\(\n|\r\n|\r)+'
    REGEX_COMMENT = r'(/\*(.|\n)*?\*/)|(//.*)|(\#.*)'

    def count_newlines(self, pattern, **kwargs):
        m = pattern
        m.replace("\r\n", "\n")
        m.replace("\r", "\n")
        return m.count("\n")
