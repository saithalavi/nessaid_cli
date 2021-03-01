# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.compiler import CompiledGrammarSet

from nessaid_cli.tokens import (
    CliToken,
    MATCH_SUCCESS,
    MATCH_PARTIAL,
    MATCH_FAILURE,
    MATCH_AMBIGUOUS
)

from nessaid_cli.elements import (
    EndOfInpuToken,
    NamedGrammar,
    GrammarRefElement,
    AlternativeInputElement,
)

from nessaid_cli.elements import (
    SequenceInputElement,
    OptionalInputElement,
)


from nessaid_cli.binding_parser.binding_objects import (
    BindingCall,
    FunctionCall,
    BindingObject,
    BindingVariable,
    NamedVariable,
    NumberedVariable,
    AssignmentStatement,
)


class ParsingResult():

    def __init__(self):
        self.result = None
        self.error = None
        self.matched_sequence = []
        self.last_token = {}
        self.offending_token = None
        self.offending_token_position = None
        self.next_tokens = []
        self.next_constant_token = None
        self.matched_values = []

    def as_dict(self):
        return {
            'result': self.result,
            'error': self.error,
            'matched_sequence': self.matched_sequence,
            'matched_values': self.matched_values,
            'offending_token': self.offending_token,
            'offending_token_position': self.offending_token_position,
            'next_tokens': self.next_tokens,
            'last_token': self.last_token,
            'next_constant_token': self.next_constant_token,
        }

    def __repr__(self):
        return self.as_dict()

    def __str__(self):
        return str(self.as_dict())

    def common_prefix(self, l):
        l.sort(reverse = False)
        if not l:
            return ""
        elif len(l) == 1:
            return l[0]
        else:
            str1 = l[0]
            str2 = l[-1]

        n1 = len(str1)
        n2 = len(str2)

        result = ""

        j = 0
        i = 0
        while(i <= n1 - 1 and j <= n2 - 1):
            if (str1[i] != str2[j]):
                break
            result += (str1[i])

            i += 1
            j += 1

        return (result)

    def set_next_tokens(self, cur_input, tokens):
        add_EOI = False
        tokens = list(tokens)
        next_tokens = set()
        self.last_token = None

        for t in tokens:
            if t:
                if t.completable:
                    _, completions = t.complete(cur_input if cur_input else "")
                    if not completions:
                        next_tokens.add(t.helpstring)
                    else:
                        for c in completions:
                            next_tokens.add(str(c))
                else:
                    next_tokens.add(t.helpstring)
            else:
                add_EOI = True

        self.next_tokens = list(next_tokens)

        if add_EOI:
            self.next_tokens.append(EndOfInpuToken())
        elif cur_input:
            common_prefix = self.common_prefix(self.next_tokens)
            if common_prefix:
                self.last_token = (cur_input, common_prefix)

        if len(self.next_tokens) == 1 and self.next_tokens[0]:
            if self.last_token:
                if self.last_token[0] == self.last_token[1]:
                    if tokens[0].completable:
                        self.next_constant_token = self.last_token[1]
            else:
                if tokens[0].completable:
                    n, completion = tokens[0].complete("")
                    if completion and len(completion) == 1:
                        self.next_constant_token = str(completion[0])


class ElementContext():

    def __init__(self, element, token_value, param_list=None):
        self._arg_values = {}
        self._num_arg_values = {}
        self._local_variables = {}
        self._element = element
        self._param_list = param_list if param_list else []
        for param in self._param_list:
            self._arg_values[param] = None

        if element.terminal_token:
            self._token_value = token_value
        else:
            self._token_value = None

    @property
    def token_value(self):
        return self._token_value

    @property
    def arg_values(self):
        return self._arg_values

    @property
    def num_arg_values(self):
        return self._num_arg_values

    @property
    def local_variables(self):
        return self._local_variables

    @property
    def param_list(self):
        return self._param_list

    def create_local_variable(self, var_name):
        self._local_variables[var_name] = NamedVariable(var_name)
        return self._local_variables[var_name]

    def set_number_arg(self, position, value):
        if position != value.var_index:
            print("Bug!!!! Debug and fix with current sequence:")
        self._num_arg_values[value.var_id] = value

    def set_argument_by_name(self, param_name, value):
        if param_name not in self._arg_values:
            raise KeyError("Parameter {} not available for this grammar".format(param_name))
        self._arg_values[param_name] = value

    def set_argument_by_index(self, index, value):
        param_name = self._param_list[index]
        self._arg_values[param_name] = value


class ExecContext():

    def __init__(self, interface, root_grammar, match_values, arglist):
        self._interface = interface
        self._root_grammar = root_grammar
        self._match_values = match_values
        self._root_arglist = [NamedVariable(param) for param in root_grammar.param_list]

        for index in range(min(len(root_grammar.param_list), len(arglist))):
            self._root_arglist[index].assign(BindingObject.create_object(arglist[index]))

        self._elements_executing = []
        self._elem_contexts = []
        self._grammar_context = []

    @property
    def root_arglist(self):
        return self._root_arglist

    def enter(self, element, position_sequence, token_value):
        # print("Enter call:", id(element), element, token_value)
        #if type(element) in [NamedGrammar, GrammarRefElement]:
        #    print("{}: {}", element._name, position_sequence)
        if (element, position_sequence) not in self._elements_executing:
            # print("Entering exec:", element)
            cur_context = None
            parent_context = None

            if self._elem_contexts:
                parent_context = self._elem_contexts[-1]

            if type(element) == NamedGrammar:
                cur_context = ElementContext(element, token_value, element.param_list)
                if not self._elements_executing:
                    arglist = self._root_arglist
                else:
                    arglist = [NamedVariable(param) for param in element.param_list]
                    for index in range(min(len(element.param_list), len(parent_context.arg_values))):
                        arglist[index].assign(parent_context.arg_values[element.param_list[index]])

                arg_index = 0
                arg_values = {}
                for arg in arglist:
                    cur_context.set_argument_by_index(arg_index, arg)
                    arg_index += 1

                self._grammar_context.append(cur_context)

            elif type(element) == GrammarRefElement:
                arg_values = []
                arglist = element.arg_list
                grammar = element.get(0)
                cur_context = ElementContext(element, token_value, grammar.param_list)
                arg_index = 0
                for arg in arglist:
                    if type(arg) == NamedVariable:
                        arg_values.append(self.resolve_named_var(arg.var_id))
                    elif type(arg) == NumberedVariable:
                        parent_context = self._elem_contexts[-1] if self._elem_contexts else None
                        num_arg = self.resolve_numbered_var(parent_context, cur_context, arg.var_id)
                        arg_values.append(num_arg)
                    else:
                        arg_values.append(BindingObject.create_object(arg))
                    cur_context.set_argument_by_index(arg_index, arg_values[-1])
                    arg_index += 1
            else:
                cur_context = ElementContext(element, token_value)

            self._elements_executing.append((element, position_sequence))
            self._elem_contexts.append(cur_context)

            if element.pre_exec_binding:
                # print("Entry-Binding code:", element.pre_exec_binding)
                self.execute_binding(parent_context, cur_context, element.pre_exec_binding)
        else:
            pass #print("Existing")

    def execute_binding(self, parent_context, element_context, binding_code):

        grammar_context = self._grammar_context[-1] if self._grammar_context else None

        for code in binding_code:
            for block in code.blocks:
                if isinstance(block, AssignmentStatement):
                    lhs = None
                    if type(block.lhs) == NamedVariable:
                        lhs = self.resolve_named_var(block.lhs.var_id)
                        if not lhs:
                            lhs = grammar_context.create_local_variable(block.lhs.var_id)

                    elif type(block.lhs) == NumberedVariable:
                        lhs = self.resolve_numbered_var(parent_context, element_context, block.lhs.var_id)

                    if lhs:
                        rhs = self.resolve_argument(parent_context, element_context, block.rhs)

                    if lhs and rhs:
                        lhs.assign(BindingObject.create_object(rhs.value))

                elif isinstance(block, BindingCall):
                    ext_fn = block.name
                    arglist = [self.resolve_argument(parent_context, element_context, arg) for arg in block.arglist]
                    argvalues = [arg.value if arg else None for arg in arglist]
                    _ = self._interface.execute_binding_call(ext_fn, False, *argvalues)
                elif isinstance(block, FunctionCall):
                    ext_fn = block.name
                    arglist = [self.resolve_argument(parent_context, element_context, arg) for arg in block.arglist]
                    argvalues = [arg.value if arg else None for arg in arglist]
                    _ = self._interface.execute_binding_call(ext_fn, True, *argvalues)

    def resolve_argument(self, parent_context, element_context, arg):
        if type(arg) == NamedVariable:
            return self.resolve_named_var(arg.var_id)
        elif type(arg) == NumberedVariable:
            return self.resolve_numbered_var(parent_context, element_context, arg.var_id)
        elif type(arg) == BindingCall:
            ext_fn = arg.name
            arglist = [self.resolve_argument(parent_context, element_context, arg) for arg in arg.arglist]
            argvalues = [arg.value if arg else None for arg in arglist]
            call_res = self._interface.execute_binding_call(ext_fn, False, *argvalues)
            return call_res
        elif type(arg) == FunctionCall:
            ext_fn = arg.name
            arglist = [self.resolve_argument(parent_context, element_context, arg) for arg in arg.arglist]
            argvalues = [arg.value if arg else None for arg in arglist]
            call_res = self._interface.execute_binding_call(ext_fn, True, *argvalues)
            return call_res
        else:
            return arg

    def resolve_named_var(self, var_id):
        arg_values = self._grammar_context[-1].arg_values
        if var_id in arg_values:
            return arg_values[var_id]

        local_vars = arg_values = self._grammar_context[-1].local_variables
        if var_id in local_vars:
            return arg_values[var_id]

        else:
            return None

    def resolve_numbered_var(self, parent_context, element_context, var_id):
        grammar_context = self._grammar_context[-1] if self._grammar_context else None
        if element_context and var_id in element_context.num_arg_values:
            return element_context.num_arg_values[var_id]
        if parent_context and var_id in parent_context.num_arg_values:
            return parent_context.num_arg_values[var_id]
        if grammar_context and var_id in grammar_context.num_arg_values:
            return grammar_context.num_arg_values[var_id]
        return None

    def exit(self, element, position_sequence):
        #print("Exit call:", id(element), element)
        if (element, position_sequence) in self._elements_executing:
            parent_context = None
            cur_element, _ = self._elements_executing.pop()
            cur_context = self._elem_contexts.pop()
            if self._elem_contexts:
                parent_context = self._elem_contexts[-1]

            if cur_element != element:
                print("\n"*5)
                print("Error in exec stack")
                print("\n"*5)

            if cur_element.terminal_token:
                parent = None
                position = element.position
                if self._elements_executing:
                    parent, _ = self._elements_executing[-1]
                    if isinstance(parent, AlternativeInputElement):
                        position = 0
                    elif parent.repeat_count > 1:
                        position = 0
                    elif cur_element.has_parenthesis:
                        position = 0

                numbered_arg = NumberedVariable("$" + str(position + 1))
                numbered_arg.assign(BindingObject.create_object(cur_context.token_value))
                cur_context.set_number_arg(position + 1, numbered_arg)

                if self._elements_executing:
                    parent, _ = self._elements_executing[-1]

                    if type(parent) in [SequenceInputElement, OptionalInputElement, NamedGrammar] or parent.terminal_token:
                        parent_context = self._elem_contexts[-1]
                        parent_context.set_number_arg(position + 1, numbered_arg)

                has_parenthesis = False
                if element.has_parenthesis:
                    has_parenthesis = True
                elif parent:
                    for i in range(element.position):
                        e = parent.get(i)
                        if (not e.terminal_token) or (e.has_parenthesis):
                            has_parenthesis = True

                if not has_parenthesis:
                    context_index = -2
                    while (type(parent) in [SequenceInputElement, AlternativeInputElement]) and (not parent.has_parenthesis):
                        parent, _ = self._elements_executing[context_index]
                        parent_context = self._elem_contexts[context_index]
                        if type(parent) != AlternativeInputElement:
                            parent_context.set_number_arg(position + 1, numbered_arg)
                        context_index -= 1

            if element.binding:
                self.execute_binding(parent_context, cur_context, element.binding)
                #print("Exit-Binding code:", element.binding)

            if type(element) == NamedGrammar:
                self._grammar_context.pop()

            #print("Exited exec:", element)
        else:
            pass #print("Exit call: Not found:", id(element), element)

class CliInterface():

    def __init__(self, grammarset):

        if not isinstance(grammarset, CompiledGrammarSet):
            raise ValueError("CompiledGrammarSet object expected")

        self._tokens = {}
        self._grammars = grammarset
        self._grammar_stack = []
        self._token_class_map = None

    @property
    def current_grammar(self):
        return self._grammar_stack[-1] if self._grammar_stack else None

    def enter_grammar(self, grammar_name):
        try:
            grammar = self._grammars.get_grammar(grammar_name)
            self._grammar_stack.append(grammar)
        except Exception as e:
            raise e

    def exit_grammar(self):
        try:
            self._grammar_stack.pop()
        except Exception as e:
            raise e

    def create_cli_token(self, token_name, tokendef=None):
        return CliToken(token_name)

    def get_token_classes(self):
        return []

    def get_token(self, name):
        if not (isinstance(name, str) and name):
            raise ValueError("Expected valid token name")

        if name not in self._tokens:
            tokendef = self._grammars.get_tokendef(name)
            if tokendef:
                if self._token_class_map is None:
                    token_classes = self.get_token_classes()
                    self._token_class_map = {t.__name__: t for t in token_classes}

                if tokendef.classname in self._token_class_map:
                    try:
                        self._tokens[name] = self._token_class_map[tokendef.classname](name, *tokendef.arglist)
                        return self._tokens[name]
                    except Exception as e:
                        print("Exception creating token object from token def:", e)

                _globals = globals()
                if tokendef.classname in _globals:
                    try:
                        self._tokens[name] =  _globals[tokendef.classname](name, *tokendef.arglist)
                        return self._tokens[name]
                    except Exception as e:
                        print("Exception creating token object from token def:", e)
            self._tokens[name] = self.create_cli_token(name, tokendef)

        return self._tokens[name]

    def get_cli_hook(self, func_name):
        return func_name

    def resolve_local_function_call(self, func_name, *args, **kwarg):
        if func_name == 'list':
            l = []
            if args:
                l += args
            return l

        if func_name == 'print':
            return print(*args)

        if func_name == 'inc':
            r = args[0]
            try:
                r = r + 1
            except Exception:
                pass
            return r

        if func_name == 'add':
            r = args[0]
            for arg in args[1:]:
                try:
                    r = r + arg
                except Exception:
                    pass
            return r

        if func_name == 'dec':
            r = args[0]
            try:
                r = r + 1
            except Exception:
                pass
            return r

        if func_name == 'dict':
            return {}

        if func_name == 'set':
            s = set()
            for arg in args:
                s.add(arg)
            return s

        if func_name == 'append':
            if not args:
                raise ValueError("append called without arguments")
            r = args[0]
            for arg in args[1:]:
                if isinstance(r, list):
                    r += [arg]
                elif isinstance(r, set):
                    r.add(arg)
            return r

        if func_name == 'update':
            if len(args) > 2:
                r = args[0]
                if isinstance(r, dict):
                    r.update({args[1]: args[2]})
                return r
            return None

        return None

    def execute_binding_call(self, func_name, local_function, *args, **kwarg):
        try:
            ext_args = [self.evaluate(arg) if arg else None for arg in args]

            if not local_function:
                if not hasattr(self, self.get_cli_hook(func_name)):
                    raise AttributeError("CLI interface missing function: {}".format(func_name))

                fn = getattr(self, self.get_cli_hook(func_name))
                res = fn(*ext_args)
            else:
                res = self.resolve_local_function_call(func_name, *ext_args, **kwarg)

            return BindingObject.create_object(res)
        except Exception as e:
            print("Exception executing binding call:", type(e), e)

    def execute_success_sequence(self, matched_sequence, match_values, arglist):

        exec_context = ExecContext(self, self.current_grammar, match_values, arglist)

        hierarchies = [token.get_element_hierarchy() for token in matched_sequence]
        token_values = match_values.copy()

        # TODO: Position based hierarchy map for entry exit keys
        # Hierarchy element should be a combination of position and element
        # Might need for executing complex recursive grammars, though trivial ones passes with this.

        for _ in matched_sequence:
            hierarchy = hierarchies.pop(0)
            token_value = token_values.pop(0)

            h_copy = hierarchy.copy()
            position_sequence = []
            position_stack = []
            while h_copy:
                parent = h_copy.pop()
                position_sequence.append(parent.position)
                position_stack.append(tuple(position_sequence))
                exec_context.enter(parent, tuple(position_sequence), token_value)

            element = hierarchy.pop(0) if hierarchy else None
            position_sequence = position_stack.pop() if position_stack else None

            exec_context.exit(element, position_sequence)

            parent = hierarchy.pop(0) if hierarchy else None
            while(element and parent):
                if type(parent) in [AlternativeInputElement]:
                    position_sequence = position_stack.pop() if position_stack else None
                    exec_context.exit(parent, position_sequence)
                elif len(parent) == (element.position + 1):
                    position_sequence = position_stack.pop() if position_stack else None
                    exec_context.exit(parent, position_sequence)
                else:
                    rest_optional = True
                    position = element.position + 1
                    while position < len(parent):
                        next = parent.get(position)
                        if next.mandatory:
                            rest_optional = False
                            break
                        elif hierarchies and next in hierarchies[0]:
                            rest_optional = False
                            break
                        position += 1
                    if rest_optional:
                        position_sequence = position_stack.pop() if position_stack else None
                        exec_context.exit(parent, position_sequence)
                    else:
                        break
                element = parent
                parent = hierarchy.pop(0) if hierarchy else None

        return [self.evaluate(v) for v in exec_context.root_arglist]

    def evaluate(self, v):
        if isinstance(v, BindingObject):
            return v.value
        if isinstance(v, BindingVariable):
            return self.evaluate(v.value)
        return v

    def match(self, tok_list, dry_run=False, last_token_complete=False, arglist=None):

        cur_token_input = None
        token_list = tok_list.copy()

        prompt_choices = set(self.current_grammar.first(root_grammar=self.current_grammar))

        res = ParsingResult()

        if not prompt_choices:
            res.result = MATCH_FAILURE
            res.offending_token = None if not token_list else token_list[0]
            res.error = "No matching start tokens"
            return res

        def set_next_tokens(res, choices):
            next_tokens = set()
            add_EOT = False
            for c in choices:
                if not c:
                    add_EOT = True
                    continue
                next_tokens.add(self.get_token(c.name))
            if add_EOT:
                next_tokens.add(EndOfInpuToken())
            return res.set_next_tokens(None if last_token_complete else cur_token_input, next_tokens)

        initial = True
        seq_copy = []
        matching_sequences = []
        matching_seq_choices = []

        while True:
            seq_complete = False

            assert len(seq_copy) == len(matching_seq_choices)

            for sequence in seq_copy:

                full_matches = []
                partial_matches = []
                choices = matching_seq_choices.pop(0)

                for c in choices:
                    if self.get_token(c.name).match(cur_token_input) == MATCH_SUCCESS:
                        full_matches.append(sequence + [c])
                    if self.get_token(c.name).match(cur_token_input) == MATCH_PARTIAL:
                        partial_matches.append(sequence + [c])

                for f in full_matches:
                    matching_sequences.append(f)

                completion = []
                for p in partial_matches:
                    token = self.get_token(p[-1].name)
                    if token.completable:
                        n, comps = token.complete(cur_token_input)
                        completion += comps

                for p in partial_matches:
                    token = self.get_token(p[-1].name)
                    if token.completable:
                        if completion:
                            if dry_run and not token_list and not last_token_complete:
                                matching_sequences.append(p)
                            elif len(completion) == 1:
                                n, comps = token.complete(cur_token_input)
                                if len(comps) == 1:
                                    matching_sequences.append(p)
                            elif token.get_value(cur_token_input):
                                matching_sequences.append(p)
                            else:
                                res.result = MATCH_FAILURE
                                res.offending_token = tok_list[len(res.matched_sequence)]
                                res.offending_token_position = len(res.matched_sequence)
                                res.error = "Ambiguous options matched for the input token: {}".format(
                                    tok_list[len(res.matched_sequence)])
                                return res
                        elif dry_run and not token_list and not last_token_complete:
                            matching_sequences.append(p)
                        elif len(partial_matches) == 1:
                            v = token.get_value(cur_token_input)
                            if v is not None:
                                matching_sequences.append(p)
                    else:
                        v = token.get_value(cur_token_input)
                        if v is not None:
                            matching_sequences.append(p)
                        elif dry_run:
                            if not token_list and not last_token_complete:
                                matching_sequences.append(p)

            if not initial:

                if not matching_sequences:
                    if len(tok_list) == len(res.matched_sequence):
                        res.result = MATCH_PARTIAL
                        res.error = "Input sequence is not complete"
                    else:
                        res.result = MATCH_FAILURE
                        res.offending_token = cur_token_input
                        res.error = "Could not match any rule for this sequence"

                        if len(tok_list) > len(res.matched_sequence):
                            res.offending_token = tok_list[len(res.matched_sequence)]
                            res.offending_token_position = len(res.matched_sequence)
                    return res

                prompt_choices = set()

                for matching_sequence in matching_sequences:
                    choices = set()
                    last_token = matching_sequence[-1]
                    if last_token == EndOfInpuToken():
                        seq_complete = True
                    else:
                        if (not token_list) and (not last_token_complete):
                            choices.add(last_token)
                        else:
                            nexts = last_token.next()
                            for c in nexts:
                                if c == EndOfInpuToken():
                                    seq_complete = True
                                else:
                                    choices.add(c)
                    matching_seq_choices.append(choices)
                    prompt_choices = prompt_choices.union(choices)

            initial = False

            if not token_list:
                if seq_complete:
                    prompt_choices.add(EndOfInpuToken())

                if prompt_choices:
                    set_next_tokens(res, prompt_choices)
                else:
                    res.result = MATCH_FAILURE
                    if cur_token_input:
                        res.offending_token = cur_token_input
                    res.error = "Could not match any rule for this sequence"
                    return res

                if matching_sequences:
                    res.matched_sequence.append(cur_token_input)
                    if not dry_run:
                        if seq_complete and len(matching_sequences) > 1:
                            matching_sequences = self.fix_sequences(matching_sequences, tok_list)

                        if seq_complete:
                            if len(matching_sequences) == 1:
                                tok_index = 0
                                match_values = []
                                for t in matching_sequences[0]:
                                    token = self.get_token(t.name)
                                    match_values.append(token.get_value(tok_list[tok_index]))
                                    tok_index += 1
                                res.matched_values = match_values
                                root_arglist = self.execute_success_sequence(matching_sequences[0], match_values, arglist)
                                for i in range(len(root_arglist)):
                                    arglist[i] = root_arglist.pop(0)
                                res.result = MATCH_SUCCESS
                            else:
                                res.result = MATCH_AMBIGUOUS
                                res.error = "{} ambiguous sequences matched for the input".format(len(matching_sequences))
                        else:
                            if len(tok_list) == len(res.matched_sequence):
                                res.result = MATCH_PARTIAL
                                res.error = "Input sequence is not complete"
                            else:
                                res.result = MATCH_FAILURE
                                res.error = "Could not successfully match any rule with the input"
                        return res
                    else:
                        res.result = MATCH_PARTIAL
                        return res
            else:
                if cur_token_input:
                    res.matched_sequence.append(cur_token_input)
                cur_token_input = token_list.pop(0)
                if matching_sequences:
                    seq_copy = matching_sequences.copy()
                else:
                    seq_copy = [[]]
                    matching_seq_choices = [prompt_choices]
                matching_sequences = []

    def fix_sequences(self, matching_sequences, tok_list):
        if len(set(len(seq) for seq in matching_sequences)) == 1:
            seq_count = len(matching_sequences)
            seq_length = len(matching_sequences[0])

            tokens_to_keep = set([i for i in range(seq_count)])

            for i in range(seq_length):
                if len(set(seq[i] for seq in matching_sequences)) == 1:
                    continue
                else:
                    toc_types = []
                    for j in range(seq_count):
                        toc = matching_sequences[j][i]
                        token = self.get_token(toc.name)
                        toc_types.append(token.match(tok_list[i]))

                    if MATCH_SUCCESS in toc_types:
                        for j in range(seq_count):
                            if j in tokens_to_keep:
                                if toc_types[j] != MATCH_SUCCESS:
                                    tokens_to_keep.remove(j)

                    if len(tokens_to_keep) == 1:
                        return [matching_sequences[list(tokens_to_keep)[0]]]

                    toc_types = []
                    for j in range(seq_count):
                        toc = matching_sequences[j][i]
                        token = self.get_token(toc.name)
                        if token.completable:
                            toc_types.append(True)
                        else:
                            toc_types.append(False)

                    if True in toc_types:
                        for j in range(seq_count):
                            if j in tokens_to_keep:
                                if toc_types[j] != True:
                                    tokens_to_keep.remove(j)

                    if len(tokens_to_keep) == 1:
                        return [matching_sequences[list(tokens_to_keep)[0]]]
        else:
            return False, "Failed to resolve ambiguity of {} sequences with different lengths"
        return matching_sequences
