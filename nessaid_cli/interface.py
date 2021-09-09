# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import asyncio

from nessaid_cli.utils import StdStreamsHolder, convert_to_python_string


from nessaid_cli.tokens import (
    CliToken,
    MATCH_SUCCESS,
    MATCH_PARTIAL,
    MATCH_FAILURE,
    MATCH_AMBIGUOUS,
    NullTokenValue
)

from nessaid_cli.elements import (
    GrammarWalkTree,
    TreeNode,
    CliArgument,
    EndOfInpuToken,
    NamedGrammar,
    GrammarRefElement,
    AlternativeInputElement,
    GrammarSpecification,
    map_grammar_arguments,
    OrderlessSetInputElement
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


class TokenCompletion(str):

    def __new__(cls, completion, helpstring):
        return super(TokenCompletion, cls).__new__(cls, completion or helpstring)

    def __init__(self, completion, helpstring):
        self.completion = completion
        self.helpstring = helpstring


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

    async def set_next_tokens(self, cli, cur_input, tokens):
        add_EOI = False
        tokens = list(tokens)
        next_tokens = set()
        self.last_token = None
        self.case_insensitive = False

        for t in tokens:
            if t:
                helpstring = await t.get_helpstring(cur_input if cur_input else "", cli=cli)
                if t.completable:
                    _, completions = await cli.complete_token(t, cur_input if cur_input else "")
                    if not completions:
                        next_tokens.add(TokenCompletion(None, helpstring))
                    else:
                        if t.case_insensitive:
                            self.case_insensitive = True
                        for c in completions:
                            h = await t.get_helpstring(str(c), cli=cli)
                            next_tokens.add(TokenCompletion(str(c), h))
                else:
                    next_tokens.add(TokenCompletion(None, helpstring))
            else:
                add_EOI = True

        self.next_tokens = list(next_tokens)

        if add_EOI:
            self.next_tokens.append(EndOfInpuToken)
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
                    _n, completion = await cli.complete_token(tokens[0], "") # noqa
                    if completion and len(completion) == 1:
                        self.next_constant_token = str(completion[0])


class ExecContext():

    def __init__(self, interface, root_grammar, arglist, stop_index = 0):
        self._counter = 1
        self._stop_index = stop_index
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
        self._element_stack_cache = {}

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
            res = convert_to_python_string(str(res), cli=self._interface)
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

    async def enter(self, element_node: TreeNode, token_value: str):

        if element_node.path in self._element_stack_cache:
            element_node = self._element_stack_cache[element_node.path]
            element_node.input_sequence.append(token_value)
            return

        element_node.input_sequence.append(token_value)

        element = element_node.element

        if element.pre_match_binding:
            await self.execute_binding(element.pre_match_binding)

        if type(element) == NamedGrammar:
            if not self._element_stack:
                for arg in self._root_arglist:
                    element_node.add_named_variable(arg)
            else:
                grammar_ref_ctx = self._element_stack[-1]
                for arg in grammar_ref_ctx.named_variables.values():
                    element_node.add_named_variable(arg)
            self._grammar_stack.append(element_node)

        elif type(element) == GrammarRefElement:
            arglist = [NamedVariable(param.name) for param in element.value.param_list]
            param_mapping = map_grammar_arguments(element.name, element.value.param_list, element.arg_list)
            for arg in arglist:
                if arg.var_id in param_mapping:
                    res = await self.resolve_argument(param_mapping[arg.var_id])
                    arg.assign(res)
                    element_node.add_named_variable(arg)
        else:
            pass
        self._element_stack.append(element_node)
        self._element_stack_cache[element_node.path] = element_node
        """
        print(f"{'%03d' % (self._counter, )}: Entered     :", element_node.path)
        self._counter += 1
        """

    async def exit(self, element_node: TreeNode):
        """
        print(f"{'%03d' % (self.counter, )}: Exit attempt:", element_node.path)
        self._counter += 1
        if self._counter == self._stop_index:
            print("Stoping to debug tree traversal")
        """
        if element_node.path not in self._element_stack_cache:
            raise Exception("Context missing in stack. Recheck!!!")

        element_node = self._element_stack_cache[element_node.path]

        stack_node = self._element_stack.pop()
        if element_node != stack_node:
            raise Exception("Wrong context at top of stack. Recheck!!!")
        del self._element_stack_cache[element_node.path]

        element = element_node.element
        parent_context = self._element_stack[-1] if self._element_stack else None
        # grammar_context = self._grammar_stack[-1] if self._grammar_stack else None
        parent = parent_context.element if parent_context else None

        position = element_node.position
        if parent:
            if isinstance(parent, AlternativeInputElement):
                position = 0
            elif parent.repeat_count > 1:
                position = 0

        numbered_arg = TokenVariable("$" + str(position + 1))
        if len(element_node.input_sequence) == 1:
            numbered_arg.assign(element_node.input_sequence[0])
        else:
            numbered_arg.assign(element_node.input_sequence)

        if parent_context:
            parent_context.add_numbered_variable(numbered_arg)

        if element.post_match_binding:
            await self.execute_binding(element.post_match_binding)

        if type(element) == NamedGrammar:
            self._grammar_stack.pop()

        element_node.reset()


class CliInterface(StdStreamsHolder):

    def __init__(self, loop, grammarset,
                 stdin=None, stdout=None, stderr=None,
                 str_cache_size=128, token_value_cache_size=128):

        if not isinstance(grammarset, GrammarSpecification):
            raise ValueError("GrammarSpecification object expected")

        self._loop = loop

        self._stop_index = 0 # To debug tree traversal bugs

        self.init_streams(stdin=stdin, stdout=stdout, stderr=stderr)

        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr

        self._tokens = {}
        self._grammars = grammarset
        self._grammar_stack = []
        self._token_class_map = None
        self._matched_values = []
        self._parse_tree = None

        self._str_cache = {}
        self._token_value_cache = {}
        self._str_cache_size = str_cache_size
        self._token_value_cache_size = token_value_cache_size

    @property
    def loop(self):
        return self._loop

    @property
    def current_grammar(self):
        return self._grammar_stack[-1] if self._grammar_stack else None

    @property
    def str_cache(self):
        return self._str_cache

    def cache_string(self, key, value):
        self._str_cache[key] = value

    def clear_str_cache(self):
        if len(self._str_cache) > self._str_cache_size:
            self._str_cache = {}

    def clear_token_value_cache(self):
        if len(self._token_value_cache) > self._token_value_cache_size:
            self._token_value_cache = {}

    def clear_caches(self):
        self.clear_str_cache()
        self.clear_token_value_cache()

    def enter_grammar(self, grammar_name):
        try:
            grammar = self._grammars.get_grammar(grammar_name)
            self._grammar_stack.append(grammar)
            self._parse_tree = GrammarWalkTree(grammar)
        except Exception as e:
            raise e

    def exit_grammar(self):
        try:
            self._grammar_stack.pop()
            if self._grammar_stack:
                self._parse_tree = GrammarWalkTree(self._grammar_stack[-1])
        except Exception as e:
            raise e

    def create_cli_token(self, token_name, helpstring=None, tokendef=None): # noqa
        return CliToken(token_name, helpstring=helpstring, cli=self)

    def get_base_token_classes(self):
        return []

    def get_token_classes(self):
        return []

    def get_token(self, name, helpstring=None):
        if not (isinstance(name, str) and name):
            raise ValueError("Expected valid token name")

        if (name, helpstring) not in self._tokens:
            self._token_miss += 1
            tokendef = self._grammars.get_tokendef(name)
            if tokendef:
                if self._token_class_map is None:
                    token_classes = self.get_base_token_classes() + self.get_token_classes()
                    self._token_class_map = {t.__name__: t for t in token_classes}

                if tokendef.classname in self._token_class_map:
                    try:
                        self._tokens[(name, helpstring)] = self._token_class_map[tokendef.classname](
                            name, *tokendef.arglist, cli=self, helpstring=helpstring)
                        return self._tokens[(name, helpstring)]
                    except Exception as e:
                        self.error("Exception creating token object from token def:", e)

                _globals = globals()
                if tokendef.classname in _globals:
                    try:
                        self._tokens[(name, helpstring)] =  _globals[tokendef.classname](
                            name, *tokendef.arglist, cli=self, helpstring=helpstring)
                        return self._tokens[(name, helpstring)]
                    except Exception as e:
                        self.error("Exception creating token object from token def:", e)
            self._tokens[(name, helpstring)] = self.create_cli_token(name, tokendef=tokendef, helpstring=helpstring)
        else:
            self._token_hit += 1

        return self._tokens[(name, helpstring)]

    def get_cli_hook(self, func_name):
        return func_name

    async def resolve_local_function_call(self, func_name, *args, **kwarg): # noqa
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

    async def get_input(self, prompt, show_char):
        raise NotImplementedError

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

        exec_context = ExecContext(self, self.current_grammar, arglist, self._stop_index)
        token_values = match_values.copy()
        sequence_copy = matched_sequence.copy()

        m = sequence_copy.pop(0)
        while m:
            node = m.node
            node_data = [node]
            token_value = token_values.pop(0)

            while node.parent:
                node = node.parent
                node_data.append(node)

            node_data.reverse()

            for node in node_data:
                await exec_context.enter(node, token_value)

            element = node_data.pop()
            await exec_context.exit(element)

            parent = node_data.pop() if node_data else None

            while(element and parent):
                if type(parent.element) in [AlternativeInputElement]:
                    await exec_context.exit(parent)
                elif not isinstance(parent.element, OrderlessSetInputElement) and parent.child_count == (element.position + 1):
                    await exec_context.exit(parent)
                else:
                    _next = []
                    rest_optional = True
                    if isinstance(parent.element, OrderlessSetInputElement):
                        filled_elems = m.lookup_path[parent.path]
                        for i in range(parent.child_count):
                            if i != element.position and i not in filled_elems:
                                _next.append(parent.get(i))
                    else:
                        position = element.position + 1
                        while position < parent.child_count:
                            _next.append(parent.get(position))
                            position += 1

                    if _next:
                        if all([n.mandatory for n in _next]):
                            rest_optional = False
                        elif sequence_copy:
                            rest_optional = True
                            for h in sequence_copy[0].node.parents:
                                if any([h.path == n.path for n in _next]):
                                    rest_optional = False
                                    break

                    if rest_optional:
                        await exec_context.exit(parent)
                    else:
                        break

                element = parent
                parent = node_data.pop() if node_data else None

            m = sequence_copy.pop(0) if sequence_copy else None

        return exec_context.root_arglist

    async def get_token_value(self, token, token_input):

        if token.cacheable:
            token_value_key = (token, token_input)
            if token_value_key in self._token_value_cache:
                self._token_value_hit += 1
                return self._token_value_cache[token_value_key]

        try:
            self._token_value_miss += 1
            if asyncio.iscoroutinefunction(token.get_value):
                value = await token.get_value(token_input, cli=self)
            else:
                value =  token.get_value(token_input, cli=self)
            if token.cacheable:
                self._token_value_cache[token_value_key] = value
            return value
        except:
            return NullTokenValue

    def get_matched_values(self):
        return self._matched_values.copy()

    async def match_token(self, token, token_input):
        try:
            if asyncio.iscoroutinefunction(token.match):
                return await token.match(token_input, cli=self)
            else:
                return token.match(token_input, cli=self)
        except:
            return MATCH_FAILURE

    async def complete_token(self, token, token_input):
        try:
            if asyncio.iscoroutinefunction(token.complete):
                return await token.complete(token_input, cli=self)
            else:
                return token.complete(token_input, cli=self)
        except:
            return 0, []

    async def match(self, tok_list, dry_run=False, last_token_complete=False, arglist=None):

        self._token_hit = 0
        self._token_miss = 0
        self._token_value_hit = 0
        self._token_value_miss = 0

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

        prompt_choices = set(self._parse_tree.first())

        res = ParsingResult()

        if not prompt_choices:
            res.result = MATCH_FAILURE
            res.offending_token = None if not token_list else token_list[0]
            res.error = "No matching start tokens"
            return res

        async def set_next_tokens(res, choices):
            next_tokens = set()
            add_EOT = False
            for c in choices:
                if not c:
                    add_EOT = True
                    continue
                next_tokens.add(self.get_token(c.name, c.helpstring))
            if add_EOT:
                next_tokens.add(EndOfInpuToken)
            return await res.set_next_tokens(self, None if last_token_complete else cur_token_input, next_tokens)

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

                try:
                    self._matched_values = []
                    i = 0
                    for t in sequence:
                        token = self.get_token(t.name)
                        value = await self.get_token_value(token, tok_list[i])
                        if value is not NullTokenValue:
                            self._matched_values.append(value)
                        i += 1
                except Exception as e:
                    print("Exception getting matched values:", type(e), e, file=self._stderr)

                for c in choices:
                    token = self.get_token(c.name)
                    if await self.match_token(token, cur_token_input) == MATCH_SUCCESS:
                        if await self.get_token_value(token, cur_token_input) is not NullTokenValue:
                            full_matches.append(sequence + [c])
                    if await self.match_token(token, cur_token_input) == MATCH_PARTIAL:
                        partial_matches.append(sequence + [c])

                for f in full_matches:
                    self.append_matching_sequence(matching_sequences, f)

                completion = []
                for p in partial_matches:
                    token = self.get_token(p[-1].name)
                    if token.completable:
                        _n, comps = await self.complete_token(token, cur_token_input) # noqa
                        completion += comps

                for p in partial_matches:
                    token = self.get_token(p[-1].name)
                    if token.completable:
                        if completion:
                            if dry_run and not token_list and not last_token_complete:
                                self.append_matching_sequence(matching_sequences, p)
                            elif len(completion) == 1:
                                _n, comps = await self.complete_token(token, cur_token_input) # noqa
                                if len(comps) == 1:
                                    val = await self.get_token_value(token, cur_token_input)
                                    if val is not NullTokenValue:
                                        self.append_matching_sequence(matching_sequences, p)
                            elif await self.get_token_value(token, cur_token_input) is not NullTokenValue:
                                self.append_matching_sequence(matching_sequences, p)
                            else:
                                res.result = MATCH_FAILURE
                                res.offending_token = tok_list[len(res.matched_sequence)]
                                res.offending_token_position = len(res.matched_sequence)
                                res.error = "Ambiguous options matched for the input token: {}".format(
                                    tok_list[len(res.matched_sequence)])
                                self.clear_caches()
                                return res
                        elif dry_run and not token_list and not last_token_complete:
                            self.append_matching_sequence(matching_sequences, p)
                        elif len(partial_matches) == 1:
                            v = await self.get_token_value(token, cur_token_input)
                            if v is not NullTokenValue:
                                self.append_matching_sequence(matching_sequences, p)
                    else:
                        v = await self.get_token_value(token, cur_token_input)
                        if v is not NullTokenValue:
                            self.append_matching_sequence(matching_sequences, p)
                        elif dry_run:
                            if not token_list and not last_token_complete:
                                self.append_matching_sequence(matching_sequences, p)

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
                    self.clear_caches()
                    return res

                prompt_choices = set()

                for matching_sequence in matching_sequences:
                    choices = set()
                    try:
                        self._matched_values = []
                        i = 0
                        for t in matching_sequence:
                            token = self.get_token(t.name)
                            value = await self.get_token_value(token, tok_list[i])
                            if value is not NullTokenValue:
                                self._matched_values.append(value)
                            i += 1
                    except Exception as e:
                        print("Exception getting matched values:", type(e), e, file=self._stderr)
                    last_token = matching_sequence[-1]
                    if last_token == EndOfInpuToken:
                        seq_complete = True
                    else:
                        if (not token_list) and (not last_token_complete):
                            choices.add(last_token)
                        else:
                            nexts = last_token.next()
                            for c in nexts:
                                if c == EndOfInpuToken:
                                    seq_complete = True
                                else:
                                    choices.add(c)
                    matching_seq_choices.append(choices)
                    prompt_choices = prompt_choices.union(choices)

            initial = False

            if not token_list:
                if seq_complete:
                    prompt_choices.add(EndOfInpuToken)

                if prompt_choices:
                    await set_next_tokens(res, prompt_choices)
                else:
                    res.result = MATCH_FAILURE
                    if cur_token_input:
                        res.offending_token = cur_token_input
                    res.error = "Could not match any rule for this sequence"
                    self.clear_caches()
                    return res

                if matching_sequences:
                    res.matched_sequence.append(cur_token_input)
                    if not dry_run:
                        if seq_complete and len(matching_sequences) > 1:
                            matching_sequences = await self.fix_sequences(matching_sequences, tok_list)

                        if seq_complete:
                            if len(matching_sequences) == 1:
                                tok_index = 0
                                match_values = []
                                self._matched_values = []
                                for t in matching_sequences[0]:
                                    token = self.get_token(t.name)
                                    match_value = await self.get_token_value(token, tok_list[tok_index])
                                    match_values.append(match_value)
                                    self._matched_values.append(match_value)
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
                        self.clear_caches()
                        return res
                    else:
                        res.result = MATCH_PARTIAL
                        self.clear_caches()
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

    def check_orderless_set_elements(self, tokens):
        elements = set([t.node.element for t in tokens])
        return True if len(elements) == 1 else False

    def append_matching_sequence(self, matching_sequences, match):
        for seq in matching_sequences:
            if len(seq) == len(match):
                if all([self.check_orderless_set_elements([seq[i], match[i]]) for i in range(len(seq))]):
                    # return
                    pass
        matching_sequences.append(match)

    async def fix_sequences(self, matching_sequences, tok_list):
        if len(set(len(seq) for seq in matching_sequences)) == 1:
            seq_count = len(matching_sequences)
            seq_length = len(matching_sequences[0])

            tokens_to_keep = set([i for i in range(seq_count)])

            orderless_set_check_failed = False
            for i in range(seq_length):
                tokens = set(seq[i] for seq in matching_sequences)
                if not self.check_orderless_set_elements(tokens):
                    orderless_set_check_failed = True

            if not orderless_set_check_failed:
                return [matching_sequences[0]]

            for i in range(seq_length):
                tokens = set(seq[i] for seq in matching_sequences)
                if len(tokens) == 1:
                    continue
                else:
                    toc_types = []
                    for j in range(seq_count):
                        toc = matching_sequences[j][i]
                        token = self.get_token(toc.name)
                        match = await self.match_token(token, tok_list[i])
                        toc_types.append(match)

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
