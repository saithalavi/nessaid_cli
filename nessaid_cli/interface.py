# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import sys
import asyncio

from nessaid_cli.utils import StdStreamsHolder, convert_to_python_string


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
    GrammarSpecification,
    map_grammar_arguments,
    TokenHierarchyElement
)

from nessaid_cli.elements import (
    SequenceInputElement,
    OptionalInputElement,
    CliArgument
)


from nessaid_cli.binding_parser.binding_objects import (
    BindingCall,
    FunctionCall,
    NamedVariable,
    TokenVariable,
    BindingVariable,
    AssignmentStatement,
)

from nessaid_cli.lex_yacc_common import (
    DollarNumber,
    DollarVariable
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
        self.case_insensitive = False

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
            'case_insensitive': self.case_insensitive,
        }

    def __repr__(self):
        return str(self.as_dict())

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
        self.case_insensitive = False

        for t in tokens:
            if t:
                if t.completable:
                    _, completions = t.complete(cur_input if cur_input else "")
                    if not completions:
                        next_tokens.add(t.helpstring)
                    else:
                        if t.case_insensitive:
                            self.case_insensitive = True
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


class ExecContext():

    def __init__(self, interface, root_grammar, arglist):
        self._interface = interface
        self.print = interface.print
        self.error = interface.error
        self._root_grammar = root_grammar
        self._root_arglist = [NamedVariable(param.name) for param in root_grammar.param_list]
        self._param_mapping = map_grammar_arguments(root_grammar.name, root_grammar.param_list, arglist)

        for param in self._root_arglist:
            if param.var_id in self._param_mapping:
                param.assign(self._param_mapping[param.var_id].value)

        self._element_stack = []
        self._grammar_stack = []

    @property
    def root_arglist(self):
        return [e.value for e in self._root_arglist]

    def resolve_variable(self, var):
        if type(var) == DollarVariable:
            grammar_context = self._grammar_stack[-1] if self._grammar_stack else None
            if var in grammar_context.named_variables:
                return grammar_context.named_variables[var]
        elif type(var) == DollarNumber:
            parent_context = self._element_stack[-1] if self._element_stack else None
            if var in parent_context.token_variables:
                return parent_context.token_variables[var]
        return None

    async def resolve_argument(self, argument):
        if type(argument) in [DollarVariable, DollarNumber]:
            return self.resolve_variable(argument)
        elif type(argument) is CliArgument:
            return await self.resolve_argument(argument.value)
        elif type(argument) == BindingCall:
            ext_fn = argument.name
            arglist = [await self.evaluate(arg) for arg in argument.arglist]
            call_res = await self._interface.execute_binding_call(ext_fn, False, *arglist)
            return call_res
        elif type(argument) == FunctionCall:
            ext_fn = argument.name
            arglist = [await self.evaluate(arg) for arg in argument.arglist]
            call_res = await self._interface.execute_binding_call(ext_fn, True, *arglist)
            return call_res
        return argument

    async def evaluate(self, arg):
        res_arg = await self.resolve_argument(arg)
        if isinstance(res_arg, BindingVariable):
            res = res_arg.value
        else:
            res = res_arg

        if isinstance(res, str):
            res = convert_to_python_string(res)
        return res

    async def execute_binding(self, binding_code):

        grammar_context = self._grammar_stack[-1] if self._grammar_stack else None

        for code in binding_code:
            for block in code.blocks:
                if isinstance(block, AssignmentStatement):
                    lhs = None
                    if type(block.lhs) == DollarVariable:
                        lhs = self.resolve_variable(block.lhs)
                        if not lhs:
                            var = NamedVariable(str(block.lhs))
                            grammar_context.add_named_variable(var)
                            lhs = var
                    elif type(block.lhs) == DollarNumber:
                        lhs = self.resolve_variable(block.lhs)

                    if lhs:
                        rhs = await self.resolve_argument(block.rhs)
                        lhs.assign(rhs)

                elif isinstance(block, BindingCall):
                    ext_fn = block.name
                    arglist = [await self.evaluate(arg) for arg in block.arglist]
                    _ = await self._interface.execute_binding_call(ext_fn, False, *arglist)
                elif isinstance(block, FunctionCall):
                    ext_fn = block.name
                    arglist = [await self.evaluate(arg) for arg in block.arglist]
                    _ = await self._interface.execute_binding_call(ext_fn, True, *arglist)

    async def enter(self, element_ctx: TokenHierarchyElement, token_value: str):

        if element_ctx in self._element_stack:
            element_ctx = [e for e in self._element_stack if e == element_ctx][0]
            element_ctx.input_sequence.append(token_value)
            return

        element_ctx.input_sequence.append(token_value)

        if element_ctx not in self._element_stack:
            element = element_ctx.element

            if element.pre_match_binding:
                await self.execute_binding(element.pre_match_binding)

            if type(element) == NamedGrammar:
                if not self._element_stack:
                    for arg in self._root_arglist:
                        element_ctx.add_named_variable(arg)
                else:
                    grammar_ref_ctx = self._element_stack[-1]
                    for arg in grammar_ref_ctx.named_variables.values():
                         element_ctx.add_named_variable(arg)
                self._grammar_stack.append(element_ctx)

            elif type(element) == GrammarRefElement:
                arglist = [NamedVariable(param.name) for param in element.value.param_list]
                param_mapping = map_grammar_arguments(element.name, element.value.param_list, element.arg_list)
                for arg in arglist:
                    if arg.var_id in param_mapping:
                        res = await self.resolve_argument(param_mapping[arg.var_id])
                        arg.assign(res)
                        element_ctx.add_named_variable(arg)
            else:
                pass
            self._element_stack.append(element_ctx)

    async def exit(self, element_ctx: TokenHierarchyElement):
        if element_ctx not in self._element_stack:
            raise Exception("Context missing in stack. Recheck!!!")

        element_ctx = [e for e in self._element_stack if e == element_ctx][0]

        stack_ctx = self._element_stack.pop()
        if element_ctx != stack_ctx:
            raise Exception("Wrong context at top of stack. Recheck!!!")

        element = element_ctx.element
        parent_context = self._element_stack[-1] if self._element_stack else None
        grammar_context = self._grammar_stack[-1] if self._grammar_stack else None
        parent = parent_context.element if parent_context else None

        position = element.position
        if parent:
            if isinstance(parent, AlternativeInputElement):
                position = 0
            elif parent.repeat_count > 1:
                position = 0

        numbered_arg = TokenVariable("$" + str(position + 1))
        if len(element_ctx.input_sequence) == 1:
            numbered_arg.assign(element_ctx.input_sequence[0])
        else:
            numbered_arg.assign(element_ctx.input_sequence)

        if parent_context:
            parent_context.add_numbered_variable(numbered_arg)

        if element.post_match_binding:
            await self.execute_binding(element.post_match_binding)

        if type(element) == NamedGrammar:
            self._grammar_stack.pop()


class CliInterface(StdStreamsHolder):

    def __init__(self, loop, grammarset, stdin=None, stdout=None, stderr=None):

        if not isinstance(grammarset, GrammarSpecification):
            raise ValueError("GrammarSpecification object expected")

        self._loop = loop

        self.init_streams(stdin=stdin, stdout=stdout, stderr=stderr)

        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr

        self._tokens = {}
        self._grammars = grammarset
        self._grammar_stack = []
        self._token_class_map = None

    @property
    def loop(self):
        return self._loop

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
                        self.error("Exception creating token object from token def:", e)

                _globals = globals()
                if tokendef.classname in _globals:
                    try:
                        self._tokens[name] =  _globals[tokendef.classname](name, *tokendef.arglist)
                        return self._tokens[name]
                    except Exception as e:
                        self.error("Exception creating token object from token def:", e)
            self._tokens[name] = self.create_cli_token(name, tokendef)

        return self._tokens[name]

    def get_cli_hook(self, func_name):
        return func_name

    async def resolve_local_function_call(self, func_name, *args, **kwarg):
        if func_name == 'list':
            l = []
            if args:
                l += args
            return l

        if func_name == 'print':
            return self.print(*args)

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

        if func_name == 'input':
            prompt = ""
            show_char = True
            if len(args):
                prompt = str(args[0])
                if len(args) > 1:
                    show_char = args[1]
            try:
                return await self.get_input(prompt, show_char)
            except:
                return ""

        return None

    async def execute_binding_call(self, func_name: str, local_function: bool, *args, **kwarg):
        try:
            ext_args = args

            if not local_function:
                if not hasattr(self, self.get_cli_hook(func_name)):
                    raise AttributeError("CLI interface missing function: {}".format(func_name))

                fn = getattr(self, self.get_cli_hook(func_name))

                if asyncio.iscoroutinefunction(fn):
                    res = await fn(*ext_args)
                else:
                    res = fn(*ext_args)
            else:
                res = await self.resolve_local_function_call(func_name, *ext_args, **kwarg)

            return res
        except Exception as e:
            self.error("Exception executing binding call:", type(e), e)

    async def execute_success_sequence(self, matched_sequence, match_values, arglist):

        exec_context = ExecContext(self, self.current_grammar, arglist)

        hierarchies = [token.get_element_hierarchy() for token in matched_sequence]
        token_values = match_values.copy()

        for _ in matched_sequence:
            hierarchy = hierarchies.pop(0)
            token_value = token_values.pop(0)

            h_copy = hierarchy.copy()
            while h_copy:
                parent = h_copy.pop()
                await exec_context.enter(parent, token_value)

            element = hierarchy.pop(0) if hierarchy else None

            await exec_context.exit(element)

            parent = hierarchy.pop(0) if hierarchy else None
            while(element and parent):
                if type(parent.element) in [AlternativeInputElement]:
                    await exec_context.exit(parent)
                elif len(parent.element) == (element.element.position + 1):
                    await exec_context.exit(parent)
                else:
                    rest_optional = True
                    position = element.element.position + 1
                    while position < len(parent.element):
                        next = parent.element.get(position)
                        if next.mandatory:
                            rest_optional = False
                            break
                        if hierarchies:
                            rest_optional = True
                            for h in hierarchies[0]:
                                if h.element == next:
                                    rest_optional = False
                                    break
                            if not rest_optional:
                                break
                        position += 1
                    if rest_optional:
                        await exec_context.exit(parent)
                    else:
                        break
                element = parent
                parent = hierarchy.pop(0) if hierarchy else None

        return exec_context.root_arglist

    async def match(self, tok_list, dry_run=False, last_token_complete=False, arglist=None):

        if not arglist:
            args = []
        else:
            args = []
            for arg in arglist:
                if isinstance(arg, CliArgument):
                    args.append(arg)
                else:
                    args.append(CliArgument(arg))

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
                                    match_value = token.get_value(tok_list[tok_index])
                                    match_values.append(match_value)
                                    tok_index += 1
                                res.matched_values = match_values
                                root_arglist = await self.execute_success_sequence(matching_sequences[0], match_values, args)
                                arglen = len(arglist)
                                for i in range(arglen):
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
