# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#


from nessaid_cli.lex_yacc_common import (
    NessaidCliLexerCommon,
    NessaidCliParserCommon,
)

from nessaid_cli.elements import (
    ConstantInputElement,
    KeywordInputElement,
    SequenceInputElement,
    OptionalInputElement,
    AlternativeInputElement,
    NamedGrammar,
    GrammarRefElement,
    UnresolvedInputElement,
    TokenClassDef,
    GrammarSpecification,
    CliParameter,
    CliArgument,
    CliTokenArgument
)

from nessaid_cli.binding_parser.binding_text_parser import NessaidCliBindingParser

from nessaid_cli.utils import convert_to_python_string


class NessaidCliLexer(NessaidCliLexerCommon):

    BINDING_STATE = 'BINDING'

    states = (
        (BINDING_STATE, 'exclusive'),
    )

    tokens = NessaidCliLexerCommon.tokens + (
        'IMPORT',
        'TOKEN',
        'OPEN_BINDING',
        'CLOSE_BINDING',
        'BOUND_CONTENT',
        'TRUE',
        'FALSE',
        'NONE',
    )

    t_BINDING_ignore = ""

    def t_IDENTIFIER(self, t):
        r'[A-Za-z_][-a-zA-Z0-9_]*'
        if t.value in NessaidCliLexer.KYWORD_TOKENS:
            t.type = NessaidCliLexer.KYWORD_TOKENS[t.value]
        return t

    """
    def t_IMPORT(self, t):
        "import"
        return t

    def t_TOKEN(self, t):
        "token"
        return t

    def t_TRUE(self, t):
        "True"
        return t

    def t_FALSE(self, t):
        "False"
        return t

    def t_NONE(self, t):
        "None"
        return t
    """

    KYWORD_TOKENS = {
        "import": 'IMPORT',
        "token": 'TOKEN',
        "True": 'TRUE',
        "False": 'FALSE',
        "None": 'NONE',
    }

    t_ignore_COMMENT = NessaidCliLexerCommon.common_COMMENT

    def t_INITIAL_OPEN_BINDING(self, t):
        r'<<'
        self.enter_state(NessaidCliLexer.BINDING_STATE)
        return t

    def t_BINDING_BOUND_CONTENT(self, t):
        r'([^>\\])+'
        self.update_counters(t)
        return t

    def t_BINDING_ESCAPED_CHAR(self, t):
        r'\\(.)'
        self.update_counters(t)
        return t

    def t_BINDING_CLOSE_BINDING(self, t):
        r'>>'
        self.exit_state(NessaidCliLexer.BINDING_STATE)
        return t

    t_BINDING_error = NessaidCliLexerCommon.t_error

    def __init__(self, stdin=None, stdout=None, stderr=None):
        # Build the lexer
        super().__init__(stdin=stdin, stdout=stdout, stderr=stderr)


class NessaidCliParser(NessaidCliParserCommon):

    tokens = NessaidCliLexer.tokens

    def p_grammar_spec(self, t):
        """grammar_spec : content empty"""
        content = t[1]
        grammar_spec = self._grammar_spec
        t[0] = grammar_spec

    def p_content(self, t):
        """content : content block
                   | empty"""
        content = t[1]
        if content is None:
            content = []
        else:
            block = t[2]
            content.append(block)
        t[0] = content

    def p_block(self, t):
        """block : named_grammar
                 | token_block
                 | unused_token"""
        grammar = t[1]
        block = grammar
        t[0] = block

    def p_token_block(self, t):
        '''token_block : TOKEN token_spec_list SEMICOLON'''
        token_spec_list = t[2]
        for token_spec in token_spec_list:
            token_name = token_spec[0]
            token_classdef = token_spec[1]
            self._grammar_spec.add_token_def(token_name, token_classdef)

    def p_token_spec_list(self, t):
        """token_spec_list : token_spec_list COMMA token_unit
                           | token_unit"""
        if len(t) == 2:
            token_spec_list = [t[1]]
        else:
            token_spec_list = t[1]
            token_spec = t[3]
            token_spec_list.append(token_spec)
        t[0] = token_spec_list

    def p_token_unit(self, t):
        '''token_unit : identifier optional_class_def'''

        token_name = t[1]
        classdef = t[2]
        token_spec = (token_name, classdef)
        t[0] = token_spec

    def p_optional_class_def(self, t):
        """optional_class_def : identifier LPAREN optional_token_arguments RPAREN
                              | empty"""
        classname = t[1]
        if classname is None:
            classname =  "CliToken"
            arglist = []
        else:
            arglist = t[3]
            if arglist is None:
                arglist = []
        classdef = TokenClassDef(classname, arglist)
        t[0] = classdef

    def p_named_grammar(self, t):
        'named_grammar : identifier optional_parameter_list COLON rule SEMICOLON'
        identifier = t[1]
        param_list = t[2]
        rule = t[4]
        named_grammar = NamedGrammar(identifier, param_list, rule)
        rule.parent = named_grammar
        self._grammar_spec.add_grammar(named_grammar)
        t[0] = named_grammar

    def p_term_multiplier(self, t):
        """term : term MULTIPLY repeater"""
        term = t[1]
        repeater = t[3]
        min_count = repeater[0]
        max_count = repeater[1]

        if min_count < 0 or max_count < 0:
            raise ValueError("Only positive repeaters allowed")

        if min_count == max_count:
            if min_count == 0:
                raise ValueError("0 repeaters not allowed. Delete the term")
            if min_count == 1:
                t[0] = term
            else:
                t[0] = SequenceInputElement((term,))
                term.parent = t[0]
                term.position = 0
                t[0].repeat_count = min_count
            return
        elif min_count == 0:
            if max_count == 1:
                t[0] = OptionalInputElement((term,))
                term.parent = t[0]
            else:
                t0 = SequenceInputElement((term,))
                term.parent = t0
                term.position = 0
                t0.repeat_count = max_count
                t[0] = OptionalInputElement((t0,))
                t0.parent = t[0]
            return

        term_copy = term.copy()
        if min_count == 1:
            block_1 = term
        else:
            block_1 = SequenceInputElement((term,))
            term.parent = block_1
            term.position = 0
            block_1.repeat_count = min_count

        opt_block = OptionalInputElement((term_copy,))
        term_copy.parent = opt_block

        block_2 = SequenceInputElement((opt_block,))
        block_2.repeat_count = max_count - min_count
        opt_block.parent = block_2
        opt_block.position = 0

        t[0] = SequenceInputElement((block_1, block_2))
        block_1.parent = t[0]
        block_2.parent = t[0]

    def p_repeater(self, t):
        """repeater : INTEGER
                    | LPAREN INTEGER RPAREN
                    | LPAREN INTEGER COLON INTEGER RPAREN"""
        if len(t) == 2:
            repeater = t[1]
            repeater_range = (int(repeater), int(repeater))
        elif len(t) == 4:
            repeater = t[2]
            repeater_range = (int(repeater), int(repeater))
        else:
            rmin = int(t[2])
            rmax = int(t[4])
            repeater_range = (min(rmin, rmax), max(rmin, rmax))
        t[0] = repeater_range

    def p_parenthesised_rule(self, t):
        """term : LPAREN rule RPAREN"""
        rule = t[2]
        t[0] = rule

    def p_optional_rule(self, t):
        """term : LBRACE rule RBRACE"""
        rule = t[2]
        if type(rule) is SequenceInputElement:
            values = rule.value
            pre_match_binding = rule.pre_match_binding
            post_match_binding = rule.post_match_binding
            opt_rule = OptionalInputElement(values)
            opt_rule.pre_match_binding = pre_match_binding
            opt_rule.post_match_binding = post_match_binding
        else:
            values = (rule, )
            opt_rule = OptionalInputElement(values)

        for elem in values:
            elem.parent = opt_rule

        t[0] = opt_rule

    def p_rule(self, t):
        """rule : unit_with_binding
                | rule_alternatives"""
        rule = t[1]
        t[0] = rule

    def p_rule_or_rule(self, t):
        """rule_alternatives : unit_with_binding OR unit_with_binding"""
        unit_1 = t[1]
        unit_2 = t[3]
        values = (unit_1, unit_2)
        alt = AlternativeInputElement(values)
        for elem in values:
            elem.parent = alt
        t[0] = alt

    def p_alternatives_or_rule(self, t):
        """rule_alternatives : rule_alternatives OR unit_with_binding"""
        alt = t[1]
        unit = t[3]
        values = alt.value + (unit, )
        alt = AlternativeInputElement(values)
        for elem in values:
            elem.parent = alt
        t[0] = alt

    def p_rule_with_binding(self, t):
        """unit_with_binding : optional_binding_block unit"""
        unit = t[2]
        binding = t[1]
        if binding:
            compiled_binding = []
            for b in binding:
                cb = self.compile_binding(b)
                compiled_binding.append(cb)
            unit.pre_match_binding = compiled_binding + unit.pre_match_binding
        t[0] = unit

    def p_unit_term(self, t):
        'unit : term_sequence'
        sequence = t[1]
        if len(sequence) == 1:
            unit = sequence[0]
        else:
            unit = SequenceInputElement(tuple(sequence))
            for elem in sequence:
                elem.parent = unit
        t[0] = unit

    def p_term_sequence(self, t):
        """term_sequence : term_sequence term_with_binding"""
        sequence = t[1]
        term = t[2]
        sequence.append(term)
        t[0] = sequence

    def p_term_sequence_unit(self, t):
        """term_sequence : term_with_binding"""
        term = t[1]
        t[0] = [term]

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

    def p_term_with_binding(self, t):
        'term_with_binding : term optional_binding_block'
        term = t[1]
        binding = t[2]
        if binding:
            compiled_binding = []
            for b in binding:
                cb = self.compile_binding(b)
                compiled_binding.append(cb)
            term.post_match_binding = term.post_match_binding + compiled_binding

        t[0] = term

    def p_term_identifier(self, t):
        'term : identifier'
        identifier = t[1]
        grammar = self._grammar_spec.get_grammar(identifier)
        if grammar:
            grammar_ref = GrammarRefElement(grammar, [])
            t[0] = grammar_ref
            return

        tokendef = self._grammar_spec.get_tokendef(identifier)
        if tokendef:
            term = identifier
            elem = KeywordInputElement(term)
            t[0] = elem
            return

        elem = UnresolvedInputElement(identifier)
        self._grammar_spec.add_unresolved_element(elem)
        t[0] = elem

    def p_term_identifier_with_args(self, t):
        'term : identifier LBRACKET optional_argument_sequence RBRACKET'
        grammarref = t[1]
        arguments = t[3]

        if arguments is None:
            arguments = []

        grammar = self._grammar_spec.get_grammar(grammarref)
        if grammar:
            elem = GrammarRefElement(grammar, arguments)
        else:
            elem = UnresolvedInputElement(grammarref, arguments)
            self._grammar_spec.add_unresolved_element(elem)
        t[0] = elem

    def p_optional_argument_sequence(self, t):
        """optional_argument_sequence : argument_sequence
                                      | empty"""
        argument_list = t[1]
        if argument_list is None:
            argument_list = []
        t[0] = argument_list

    def p_optional_token_arguments(self, t):
        """optional_token_arguments : token_argument_sequence
                                    | empty"""
        argument_list = t[1]
        if argument_list is None:
            argument_list = []
        t[0] = argument_list

    def p_argument_sequence(self, t):
        """argument_sequence : argument_sequence COMMA argument
                             | argument"""
        arglist = t[1]
        if len(t) == 2:
            arglist = [arglist]
        else:
            arg = t[3]
            arglist.append(arg)
        t[0] = arglist

    def p_token_argument_sequence(self, t):
        """token_argument_sequence : token_argument_sequence COMMA token_argument
                                   | token_argument"""
        arglist = t[1]
        if len(t) == 2:
            arglist = [arglist]
        else:
            arg = t[3]
            arglist.append(arg)
        t[0] = arglist

    def p_argument(self, t):
        """argument : argument_types"""
        arg = t[1]
        t[0] = CliArgument(arg)

    def p_token_argument(self, t):
        """token_argument : basic_types"""
        arg = t[1]
        t[0] = CliTokenArgument(arg)

    def p_argument_with_param_name(self, t):
        """argument : parameter_name ASSIGN argument_types"""
        param = t[1]
        arg = t[3]
        t[0] = CliArgument(arg, param_name=param)

    def p_token_argument_with_param_name(self, t):
        """token_argument : token_parameter_name ASSIGN basic_types"""
        param = t[1]
        arg = t[3]
        t[0] = CliTokenArgument(arg, param_name=param)

    def p_argument_types(self, t):
        """argument_types : dollar_id
                          | basic_types"""
        arg = t[1]
        t[0] = arg

    def p_basic_types(self, t):
        """basic_types : number
                       | string_object
                       | boolean_true
                       | boolean_false
                       | none_object"""
        arg = t[1]
        t[0] = arg

    def p_string_object(self, t):
        """string_object : quoted_string"""
        quoted_string = t[1]
        actual_string = quoted_string[1:-1]
        string_object = convert_to_python_string(actual_string)
        t[0] = string_object

    def p_boolean_true(self, t):
        """boolean_true : TRUE"""
        t[0] = True

    def p_boolean_false(self, t):
        """boolean_false : FALSE"""
        t[0] = False

    def p_none_object(self, t):
        """none_object : NONE"""
        t[0] = None

    def p_term_quoted_string(self, t):
        'term : string_object'
        string_object = t[1]
        elem = ConstantInputElement(string_object)
        t[0] = elem

    def p_identifier(self, t):
        """identifier : IDENTIFIER
                      | usable_keywords"""
        identifier = t[1]
        t[0] = identifier

    def p_usable_keywords(self, t):
        """usable_keywords : IMPORT
                           | TOKEN
                           | TRUE
                           | FALSE
                           | NONE"""
        keyword = t[1]
        t[0] = keyword

    def p_optional_binding_block(self, t):
        """optional_binding_block : binding_block_sequence
                                  | empty"""
        binding = t[1] if t[1] else []
        t[0] = binding

    def p_binding_block_sequence(self, t):
        """binding_block_sequence : binding_block_sequence binding_block
                                  | binding_block"""
        if len(t) == 2:
            binding_block = t[1]
            binding_block_sequence = []
        else:
            binding_block = t[2]
            binding_block_sequence = t[1]

        if binding_block:
            binding_block_sequence.append(binding_block)
        t[0] = binding_block_sequence

    def p_binding_block(self, t):
        'binding_block : OPEN_BINDING binding_body CLOSE_BINDING'
        binding_text = t[2]
        t[0] = binding_text

    def p_binding_body(self, t):
        """binding_body : binding_text
                        | empty"""
        binding_text = t[1] if t[1] else ""
        t[0] = binding_text

    def p_binding_text(self, t):
        '''binding_text : binding_text binding_segment
                        | binding_segment'''

        if len(t) == 2:
            binding_segment = t[1]
            binding_text = binding_segment
        else:
            binding_text = t[1]
            binding_segment = t[2]
            binding_text += binding_segment

        t[0] = binding_text

    def p_binding_segment(self, t):
        """binding_segment : BOUND_CONTENT
                           | ESCAPED_CHAR"""
        binding_segment = t[1]
        t[0] = binding_segment

    def p_optional_parameter_list(self, t):
        """optional_parameter_list : LBRACKET parameter_list RBRACKET
                                   | LBRACKET empty RBRACKET
                                   | empty"""
        lbracket = t[1]
        if lbracket is None:
            t[0] =  []
        else:
            param_list = t[2]
            if param_list is None:
                t[0] =  []
            else:
                t[0] = param_list

    def p_parameter_list(self, t):
        """parameter_list : parameter_list COMMA parameter
                          | parameter"""
        if len(t) == 2:
            parameter = t[1]
            param_list = [parameter]
        else:
            parameter = t[3]
            param_list = t[1]
            param_list.append(parameter)
        t[0] = param_list

    def p_parameter(self, t):
        """parameter : parameter_name"""
        param = t[1]
        t[0] = CliParameter(param)

    def p_parameter_with_defvalue(self, t):
        """parameter : parameter_name ASSIGN parameter_value"""
        param = t[1]
        value = t[3]
        t[0] = CliParameter(param, defvalue=value, has_def_value=True)

    def p_parameter_name(self, t):
        """parameter_name : dollar_name"""
        param_id = t[1]
        t[0] = param_id

    def p_token_parameter_name(self, t):
        """token_parameter_name : identifier"""
        param_id = t[1]
        t[0] = param_id

    def p_parameter_value(self, t):
        """parameter_value : string_object
                           | dollar_name
                           | number"""
        parameter_value = t[1]
        t[0] = parameter_value

    def p_unused_token(self, t):
        """unused_token : eof
                        | AND
                        | NEWLINE
                        | ESCAPED_NEWLINE
                        | SINGLE_BACKSLASH
                        | QUOTED_INCOMPLETE_STR
                        | quoted_split_string"""
        print("Syntax error (Unused token)")
        self.p_error(t)

    def parse(self, input_str):
        self.lexer.enter_state(NessaidCliLexer.INITIAL_STATE)
        return self.parser.parse(input_str, lexer=self.lexer.lexer)

    def __init__(self, stdin=None, stdout=None, stderr=None):
        self._grammar_spec = GrammarSpecification()
        self._lexer = NessaidCliLexer(stdin=stdin, stdout=stdout, stderr=stderr)
        self.binding_parser = NessaidCliBindingParser(stdin=stdin, stdout=stdout, stderr=stderr)
        super().__init__(stdin=stdin, stdout=stdout, stderr=stderr)


def compile(input_str: str):
    """Compile the grammar specification in str format to a GrammarSpecification object

    :param input_str: The grammar specification as string
    :returns: a GrammarSpecification object which will contain the parsed grammars and token definitions
    :rtype: GrammarSpecification
    """

    parser = NessaidCliParser()
    output = parser.parse(input_str)
    return output