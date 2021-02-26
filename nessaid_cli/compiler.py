# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import json
import ply.lex as lex
import ply.yacc as yacc

from nessaid_cli.tokens import TokenClassDef
from nessaid_cli.lex_yacc_common import NessaidCliLexerCommon
from nessaid_cli.binding_parser.binding_text_parser import NessaidCliBindingParser

from nessaid_cli.binding_parser.binding_objects import (
    NamedVariable,
    NumberedVariable
)

from nessaid_cli.elements import (
    NamedGrammar,
    GrammarRefElement,
    SequenceInputElement,
    OptionalInputElement,
    ConstantInputElement,
    KeywordInputElement,
    UnresolvedInputElement,
    ElementTreeCreator,
)


class NessaidCliLexer(NessaidCliLexerCommon):

    states = (
        ('QUOTE','exclusive'),
        ('BINDING','exclusive'),
    )

    tokens = NessaidCliLexerCommon.tokens + (
        'IMPORT',
        'TOKEN',
        'OPEN_QUOTE',
        'CLOSE_QUOTE',
        'QUOTED_CONTENT',
        'ESCAPED_CHAR',
        'ESCAPED_NEWLINE',
        'OPEN_BINDING',
        'CLOSE_BINDING',
        'BOUND_CONTENT',
    )

    t_ignore  = ' \t'
    t_QUOTE_ignore = ""
    t_BINDING_ignore = ""

    def t_IMPORT(self, t):
        "import"
        return t

    def t_TOKEN(self, t):
        "token"
        return t

    def t_ignore_COMMENT(self, t):
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    t_ignore_COMMENT.__doc__ = NessaidCliLexerCommon.REGEX_COMMENT

    def t_NEWLINE(self, t):
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    t_NEWLINE.__doc__ = NessaidCliLexerCommon.REGEX_MULTI_NEWLINE

    def t_INITIAL_OPEN_QUOTE(self, t):
        r'\"'
        self.enter_state('QUOTE')
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
        pass

    t_QUOTE_ESCAPED_NEWLINE.__doc__ = NessaidCliLexerCommon.REGEX_ESCAPED_NEWLINE

    def t_QUOTE_CLOSE_QUOTE(self, t):
        r'\"'
        self.exit_state('QUOTE')
        return t

    def t_INITIAL_OPEN_BINDING(self, t):
        r'<<'
        self.enter_state('BINDING')
        return t

    def t_BINDING_BOUND_CONTENT(self, t):
        r'([^>\\])+'
        count = self.count_newlines(t.value)
        t.lexer.lineno += count
        return t

    def t_BINDING_ESCAPED_CHAR(self, t):
        r'\\(.)'
        count = self.count_newlines(t.value)
        t.lexer.lineno += count
        return t

    def t_BINDING_CLOSE_BINDING(self, t):
        r'>>'
        #print(t.value)
        self.exit_state('BINDING')
        #print("BINDING_CLOSE_BINDING:", t.value)
        #print(t)
        return t

    def t_error(self, t):
        print("INITIAL: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    def t_QUOTE_error(self, t):
        #print(t.value)
        print("QUOTE: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    def t_BINDING_error(self, t):
        #print(t.value)
        print("BINDING: Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        count = self.count_newlines(t.value)
        t.lexer.lineno += count

    def enter_state(self, state):
        self._lex_states.append(state)
        self.lexer.begin(state)

    def exit_state(self, state):
        curstate = self._lex_states.pop()
        assert curstate == state
        self.lexer.begin(self._lex_states[-1] if self._lex_states else 'INITIAL')

    def __init__(self):
        # Build the lexer
        self._lex_states = []
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


class CompiledGrammarSet():
    """Class to hold grammar and token definitions for usage in python code"""

    GRAMMARS = 'grammars'
    TOKENDEFS = 'tokendefs'

    def __init__(self, grammars, tokendefs):
        self._grammars = {grammar.name: grammar for grammar in grammars}
        self._token_defs = tokendefs

    def get_grammar(self, name: str) -> NamedGrammar:
        """Get the Grammar object to use with python code

        :param name: The name of the grammar definition
        :returns: An object of NamedGrammar associated with the grammar definition
        :rtype: NamedGrammar
        """

        if name in self._grammars:
            return self._grammars[name]
        return None

    def get_tokendef(self, token_name):
        """Get the definition for token class, an object of TokenClassDef

        :param token_name: The name used in the grammar specification for the token
        :returns: A token definition, an object of TokenClassDef or None for basic constant string tokens
        :rtype: TokenClassDef
        """

        if self._token_defs and token_name in self._token_defs:
            return self._token_defs[token_name]
        return None

    def json(self):
        json_dict = {
            CompiledGrammarSet.GRAMMARS: {},
            CompiledGrammarSet.TOKENDEFS: {},
        }

        for g in self._grammars:
            json_dict[CompiledGrammarSet.GRAMMARS][g] = self._grammars[g].as_dict()

        for t in self._token_defs:
            if self._token_defs[t]:
                json_dict[CompiledGrammarSet.TOKENDEFS][t] = self._token_defs[t].as_dict()
            else:
                json_dict[CompiledGrammarSet.TOKENDEFS][t] = None

        return json.dumps(json_dict)

    @staticmethod
    def from_json(json_str):
        json_dict = json.loads(json_str)
        tree_creator = ElementTreeCreator(json_dict)
        grammars = tree_creator.get_grammars()
        token_defs = tree_creator.get_token_defs()
        return CompiledGrammarSet(grammars, token_defs)


class NessaidCliParser():

    tokens = NessaidCliLexer.tokens

    def import_file(self, import_identifier):
        return import_identifier

    def process_error(self, err):
        raise Exception(err)

    def p_grammar_file(self, t):
        """grammar_file : content empty"""
        t0 = t[1]
        for k, v in self._unresolved_tokens.items():
            if k in self._grammar_map:
                for elem in v:
                    args = elem.arg_list
                    parent = elem.parent
                    if isinstance(parent._value, tuple):
                        values = list(parent._value)
                        values[elem.position] = GrammarRefElement(self._grammar_map[k], args)
                        values[elem.position].parent = elem.parent
                        elem.copy_extras(values[elem.position])
                        parent._value = tuple(values)
        t[0] = CompiledGrammarSet(t0, self._token_defs)

    def p_content(self, t):
        """content : content block
                   | empty"""

        t1 = t[1]
        if t1 is None:
            t0 = []
        else:
            t2 = t[2]
            if t2 is None:
                t0 = t1
            else:
                t0 = t1 + [t2]
        t[0] = t0

    def p_block(self, t):
        """block : import_block
                 | token_block
                 | binding_block
                 | grammar
                 | unused_token"""
        t0 = t[1]
        t[0] = t0
        #print("Block matched:", t[0])

    def p_import_block(self, t):
        '''import_block : IMPORT IDENTIFIER SEMICOLON
                        | IMPORT quoted_string SEMICOLON'''
        # print("IMPORT:", t[2])

        import_file = self.import_file(t[2])
        if import_file:
            if not import_file in self._import_files:
                self._import_files.append(import_file)
            else:
                print("Duplicate import:", import_file)
        else:
            print("Import failed:", import_file)
        t[0] = None

    def p_token_block(self, t):
        '''token_block : TOKEN identifier optional_class_def SEMICOLON'''

        #print("TOKEN:", t[2])

        token_name = t[2]
        if token_name in self._token_defs:
            print("Duplicate token declaration:", token_name)
        classdef = t[3]
        self._token_defs[token_name] = classdef

    def p_grammar_token(self, t):
        'grammar : identifier optional_parameter_list COLON optional_binding rule SEMICOLON'

        grammar_name = t[1]
        if grammar_name in self._grammar_map:
            self.process_error("Duplicate")

        rule = t[5]
        binding_text = t[4]

        binding = self.compile_binding(binding_text)

        param_list = t[2]

        t0 = NamedGrammar(grammar_name, param_list, rule)

        if binding:
            t0.pre_exec_binding = [binding]
            t0.has_binding = True

        if rule.has_binding:
            t0.has_binding = True

        self._grammar_map[grammar_name] = t0

        #print("Grammar matched:", t[0])
        self._processed_grammars.append(t0)
        t[0] = t0

    def p_optional_class_def(self, t):
        """optional_class_def : identifier LPAREN optional_arguments RPAREN
                              | empty"""
        t1 = t[1]
        if t1 is None:
            t0 =  None
        else:
            classname = t1
            t3 = t[3]
            if t3 is None:
                params = []
            else:
                params = t3
            t0 = TokenClassDef(classname, params)
        t[0] = t0

    def p_optional_parameter_list(self, t):
        """optional_parameter_list : LBRACKET parameter_list RBRACKET
                                   | LBRACKET empty RBRACKET
                                   | empty"""
        t1 = t[1]
        if t1 is None:
            t0 =  []
        else:
            t2 = t[2]
            if t2 is None:
                t0 =  []
            else:
                t0 = t[2]
        t[0] = t0

    def p_parameter_list(self, t):
        """parameter_list : parameter_list COMMA parameter
                          | parameter"""
        t1 = t[1]
        if len(t) == 2:
            t0 = [t1]
        else:
            t3 = t[3]
            t1.append(t3)
            t0 = t1
        t[0] = t0

    def p_parameter(self, t):
        """parameter : DOLLAR_VAR_ID"""
        t0 = t[1]
        t[0] = t0

    def p_optional_binding(self, t):
        """optional_binding : binding_block
                            | empty"""
        t1 = t[1]
        t0 = t1
        t[0] = t0

    def p_rule_and_term(self, t):
        """rule : rule term
                | rule AND term"""
        t1 = t[1]
        t2 = t[len(t)-1]
        t0 = t1.handle_sequencing(t2)
        t[0] = t0
        #print("p_rule_and_term matched:", t1, t2, " -> ", t[0])

    def p_rule_or_term(self, t):
        'rule : rule OR term'

        t1 = t[1]
        t2 = t[3]

        t0 = t1.handle_alternatives(t2)
        t[0] = t0
        #print("rule_or_rule matched: ", t1, t2, "->", t[0])

    def p_term_multiplier(self, t):
        """term : term MULTIPLY repeater"""
        t1 = t[1]
        repeater = t[3]
        min_count = repeater[0]
        max_count = repeater[1]

        if min_count < 0 or max_count < 0:
            raise ValueError("Only positive repeaters allowed")

        if min_count == max_count:
            if min_count == 0:
                raise ValueError("0 repeaters not allowed. Delete the term")
            if min_count == 1:
                t[0] = t[1]
            else:
                t[0] = SequenceInputElement((t1,))
                t1.parent = t[0]
                t1._position = 0
                t[0].repeat_count = min_count
            return
        elif min_count == 0:
            if max_count == 1:
                t[0] = OptionalInputElement((t1,))
                t1.parent = t[0]
            else:
                t0 = SequenceInputElement((t1,))
                t1.parent = t0
                t1._position = 0
                t0.repeat_count = max_count
                t[0] = OptionalInputElement((t0,))
                t0.parent = t[0]
            return
        """
        if max_count == min_count + 1:
            t0 = SequenceInputElement((t1,))
            t1.parent = t0
            t1._position = 0
            t0.repeat_count = max_count
            t[0] = OptionalInputElement((t0,))
            t0.parent = t[0]
            return
        """

        t1_copy = t1.copy()
        if min_count == 1:
            block_1 = t1
        else:
            block_1 = SequenceInputElement((t1,))
            t1.parent = block_1
            t1._position = 0
            block_1.repeat_count = min_count

        opt_block = OptionalInputElement((t1_copy,))
        t1_copy.parent = opt_block

        block_2 = SequenceInputElement((opt_block,))
        block_2.repeat_count = max_count - min_count
        opt_block.parent = block_2
        opt_block._position = 0

        t[0] = SequenceInputElement((block_1, block_2))
        block_1.parent = t[0]
        block_2.parent = t[0]

    def p_rule_term(self, t):
        """rule : term"""
        t[0] = t[1]

    def p_term_binding(self, t):
        """term : term binding_block"""
        t1 = t[1]
        t2 = t[2]

        binding = self.compile_binding(t2)
        t0 = t1.handle_binding(binding)
        t[0] = t0

    def p_term_paren_rule(self, t):
        'term : LPAREN optional_binding rule RPAREN'
        t1 = t[3]
        t2 = t[2]
        binding = self.compile_binding(t2)
        t0 = t1.handle_parenthesis([binding] if binding else None)
        t[0] = t0

    def p_repeater(self, t):
        """repeater : INTEGER
                    | LPAREN INTEGER COLON INTEGER RPAREN"""
        t1 = t[1]
        if len(t) == 2:
            t0 = (int(t1), int(t1))
        else:
            t2 = int(t[2])
            t4 = int(t[4])
            t0 = (min(t2, t4), max(t2, t4))
        t[0] = t0

    def p_term_braced_rule(self, t):
        'term : LBRACE optional_binding rule RBRACE'
        t1 = t[3]
        t2 = t[2]
        binding = self.compile_binding(t2)
        t0 = t1.handle_brace([binding] if binding else None)
        t[0] = t0
        #print("p_term_braced_rule matched:", t[2], " -> ", t[0])

    def p_term_identifier_with_args(self, t):
        'term : identifier LBRACKET optional_arguments RBRACKET'
        grammarref = t[1]
        arguments = t[3]
        if arguments is None:
            arguments = []
        if grammarref in self._grammar_map:
            t0 = GrammarRefElement(self._grammar_map[grammarref], arguments)
        else:
            print("Unresolvec grammar: {}".format(grammarref))
            t0 = UnresolvedInputElement(grammarref, arguments)
            if grammarref not in self._unresolved_tokens:
                self._unresolved_tokens[grammarref] = []
            self._unresolved_tokens[grammarref].append(t0)
        t[0] = t0

    def p_optional_arguments(self, t):
        """optional_arguments : argument_list
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
                    | quoted_string"""
        t0 = t[1]
        t[0] = t0

    def p_dollar_id(self, t):
        """dollar_id : dollar_name
                     | dollar_number"""
        t1 = t[1]
        t[0] = t1

    def p_dollar_name(self, t):
        'dollar_name : DOLLAR_VAR_ID'
        t1 = t[1]
        t[0] = NamedVariable(t1)

    def p_dollar_number(self, t):
        'dollar_number : DOLLAR_NUMBER_ID'
        t1 = t[1]
        t[0] = NumberedVariable(t1)

    def p_number(self, t):
        """number : integer
                  | float"""
        t1 = t[1]
        t[0] = t1

    def p_integer(self, t):
        """integer : INTEGER"""
        t1 = t[1]
        try:
            t[0] = int(t1)
        except Exception:
            t[0] = 0

    def p_float(self, t):
        """float : FLOAT"""
        t1 = t[1]
        try:
            t[0] = float(t1)
        except Exception:
            t[0] = 0.0

    def p_term_identifier(self, t):
        'term : identifier'
        t1 = t[1]
        if t1 in self._grammar_map:
            t0 = GrammarRefElement(self._grammar_map[t1], [])
        elif t1 in self._token_defs:
            t0 = KeywordInputElement(t1)
        else:
            print("Unresolved Token:", t1)
            t0 = UnresolvedInputElement(t1)
            if t1 not in self._unresolved_tokens:
                self._unresolved_tokens[t1] = []
            self._unresolved_tokens[t1].append(t0)
        t[0] = t0

    def p_term_quoted_string(self, t):
        'term : quoted_string'
        #print(t[1])
        t[0] = ConstantInputElement(t[1])

    def p_identifier(self, t):
        """identifier : IDENTIFIER
                      | usable_keywords"""
        t1 = t[1]
        t[0] = t1

    def p_usable_keywords(self, t):
        """usable_keywords : IMPORT
                           | TOKEN"""
        t[0] = t[1]

    def p_binding_block(self, t):
        'binding_block : OPEN_BINDING binding_body CLOSE_BINDING'
        t2 = t[2]
        t[0] = t2

    def p_binding_body(self, t):
        """binding_body : binding_text
                        | empty"""
        t1 = t[1]
        if t1 is None:
            t0 = ""
        else:
            t0 = t1
        t[0] = t0

    def p_binding_text(self, t):
        '''binding_text : binding_text binding_segment
                        | binding_segment'''

        t1 = t[1]
        if len(t) == 2:
            t0 = t1
        else:
            t2 = t[2]
            t0 = t1 + t2
        t[0] = t0

    def p_binding_segment(self, t):
        """binding_segment : BOUND_CONTENT
                           | ESCAPED_CHAR"""
        # import pdb; pdb.set_trace()
        if t[1] in ["\\\\", "\\>"]:
            t[1] = t[1][1:]
        t[0] = t[1]

    def p_quoted_string(self, t):
        'quoted_string : OPEN_QUOTE quote_body CLOSE_QUOTE'
        t2 = t[2]

        replace_patterns = {
            "\\n": "\n",
            "\\r": "\r",
            "\\t": "\t",
        }

        for k, v in replace_patterns.items():
            t2 = t2.replace(k, v)

        t[0] = t2

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

    def p_error(self, t):
        if t:
            print("Syntax error at '%s'" % t.value)

    def p_unused_token(self, t):
        """unused_token : ESCAPED_NEWLINE
                        | ASSIGN
                        | eof"""

        print("Syntax error (Unused token) at '%s'" % t.value)
        t[0] = None

    def compile_binding(self, binding):
        if binding is None:
            return None
        r, binding_code = self.binding_parser.parse(binding)
        #print("Binding parsed:", r, binding_code)
        if not r:
            print("Failed to parse binding code")
            print("Code:")
            print(binding)
            print(binding_code)
            raise Exception("Failed to parse binding code")
        return binding_code

    def __init__(self):
        self._import_files = []
        self._processed_grammars = []
        self.binding_parser = NessaidCliBindingParser()

        self._grammar_map = {}
        self._token_defs = {}
        self.lexer = NessaidCliLexer()
        self.parser = yacc.yacc(module=self, debug=False, write_tables=False)
        self._unresolved_tokens = {}

    def parse(self, input_str):
        return self.parser.parse(input_str, lexer=self.lexer.lexer)


def compile(input_str: str) -> CompiledGrammarSet:
    """Compile the grammar specification in str format to a CompiledGrammarSet object

    :param input_str: The grammar specification as string
    :returns: a CompiledGrammarSet object which will contain the parsed grammars and token definitions
    :rtype: CompiledGrammarSet
    """

    parser = NessaidCliParser()
    output = parser.parse(input_str)
    if not output:
        raise Exception("Failed to parse grammar")
    """
    try:
        json_dict = output.json()
    except:
        pass
    """
    return output