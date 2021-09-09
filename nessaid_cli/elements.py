# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.tokens import CliToken, MATCH_FAILURE, NullTokenValue
from nessaid_cli.lex_yacc_common import DollarVariable
from nessaid_cli.utils import ExtendedString


class CliParameter(ExtendedString):

    def __init__(self, value, defvalue=None, has_def_value=False):
        self.defvalue = None
        self.has_def_value = False
        if type(has_def_value) is not bool:
            raise AttributeError("Attribute has_def_value should be Boolean")
        super().__init__(value, defvalue=defvalue, has_def_value=has_def_value)

    def __repr__(self):
        if not self.has_def_value:
            return super().__repr__()
        else:
            return "{}={}".format(str(self), self.defvalue)

    @property
    def name(self):
        return str(self)

class CliArgument():

    def __init__(self, value, param_name=None):
        if param_name is not None:
            if type(param_name) is not DollarVariable:
                raise AttributeError("Attribute param_name should be DollarVariable")
        self._value = value
        self._param_name = param_name

    @property
    def value(self):
        return self._value

    @property
    def param_name(self):
        return self._param_name

    def __repr__(self):
        if not self.param_name:
            return str(self.value)
        else:
            return "{}={}".format(str(self.param_name), str(self.value))


class CliTokenArgument(CliArgument):

    def __init__(self, value, param_name=None):
        if param_name is not None:
            if type(param_name) is not str:
                raise AttributeError("Attribute param_name should be str")
        self._value = value
        self._param_name = param_name


class DuplicateDefinitionException(Exception):

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return 'DuplicateDefinitionException("{}")'.format(self._name)

    def __str__(self):
        return 'DuplicateDefinitionException("{}")'.format(self._name)


class DuplicateTokendefException(Exception):

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return 'DuplicateTokendefException("{}")'.format(self._name)

    def __str__(self):
        return 'DuplicateTokendefException("{}")'.format(self._name)


class ArgumentError(Exception):
    pass


class InputElement():

    def __init__(self, helpstring=None):
        self._parent = None
        self._value = None
        self._pre_match_binding = ()
        self._post_match_binding = ()
        self._repeat_count = 1
        self._help_string = helpstring

    def copy_extras(self, cp):
        cp._pre_match_binding = self._pre_match_binding
        cp._post_match_binding = self._post_match_binding
        cp.repeat_count = self.repeat_count

    def __str__(self):
        return repr(self)

    def __len__(self):
        return 1

    @property
    def repeat_count(self):
        return self._repeat_count

    @repeat_count.setter
    def repeat_count(self, value):
        if isinstance(value, int) and value > 0:
            self._repeat_count = value
        else:
            raise ValueError("Repeater should be > 0")

    @property
    def value(self):
        return self._value

    @property
    def parent(self):
        try:
            return self._parent
        except:
            return None

    @parent.setter
    def parent(self, p):
        if not isinstance(p, InputElementHolder):
            raise ValueError("Expected InputElementCollection object for parent")
        self._parent = p

    def validate_binding(self, b):
        if not isinstance(b, tuple):
            for e in b:
                if not isinstance(e, str):
                    raise ValueError("Expected str object for binding code")
            raise ValueError("Expected list object for binding code segments")
        return b

    @property
    def pre_match_binding(self):
        return self._pre_match_binding

    @pre_match_binding.setter
    def pre_match_binding(self, b):
        self._pre_match_binding = self.validate_binding(b)

    @property
    def post_match_binding(self):
        return self._post_match_binding

    @post_match_binding.setter
    def post_match_binding(self, b):
        self._post_match_binding = self.validate_binding(b)

    @property
    def mandatory(self):
        return False

    @property
    def helpstring(self):
        return self._help_string


class ConstantInputElement(InputElement):

    def __init__(self, keyword, helpstring=None):
        super().__init__(helpstring)
        self._value = keyword

    def copy(self):
        cp = ConstantInputElement(self._value, helpstring=self.helpstring)
        self.copy_extras(cp)
        return cp

    def __repr__(self, verbose=True): # noqa
        return self._value

    @property
    def mandatory(self):
        return True


class KeywordInputElement(InputElement):

    def __init__(self, keyword, helpstring=None):
        super().__init__(helpstring)
        if isinstance(keyword, str):
            self._value = keyword
        else:
            raise ValueError("Expected str object")

    def copy(self):
        cp = KeywordInputElement(self._value, helpstring=self.helpstring)
        self.copy_extras(cp)
        return cp

    def __repr__(self, verbose=True): # noqa
        return self._value

    @property
    def mandatory(self):
        return True


class InputElementHolder(InputElement):
    pass


class InputElementCollection(InputElementHolder):

    def __init__(self, sequence):
        super().__init__()
        self._mandatory = None
        if isinstance(sequence, tuple):
            self._value = sequence
        else:
            raise ValueError("Expected tuple object")

    def __len__(self):
        return len(self._value)

    def copy(self):
        val = tuple([v.copy() for v in self._value])
        cp = self.__class__(val)
        for v in val:
            v.parent = cp
        self.copy_extras(cp)
        return cp


class SequenceInputElement(InputElementCollection):

    def __repr__(self, verbose=True):
        _repr = "Seq" if verbose else ""
        if self.repeat_count > 1:
            _repeat = "*{}".format(self.repeat_count)
        else:
            _repeat = ""
        return _repr + '(' + ", ".join([e.__repr__(verbose=False) for e in self.value]) + ')' + _repeat

    def __len__(self):
        if self.repeat_count > 1:
            assert len(self._value) == 1
            return self.repeat_count
        else:
            return len(self._value)

    @property
    def mandatory(self):
        if self._mandatory is not None:
            return self._mandatory
        for elem in self._value:
            if elem.mandatory:
                self._mandatory = True
                return True
        self._mandatory = False
        return False


class OrderlessSetInputElement(InputElementCollection):

    def __init__(self, sequence):
        super().__init__(sequence)
        self._mandatory = None
        if isinstance(sequence, tuple):
            self._value = sequence
        else:
            raise ValueError("Expected tuple object")

    def __len__(self):
        return len(self._value)

    def __repr__(self, verbose=True): # noqa
        return "Set" + '{' + ", ".join([e.__repr__(verbose=False) for e in self.value]) + '}'

    def copy(self):
        val = tuple([v.copy() for v in self._value])
        cp = self.__class__(val)
        for v in val:
            v.parent = cp
        self.copy_extras(cp)
        return cp

    @property
    def mandatory(self):
        if self._mandatory is not None:
            return self._mandatory
        for elem in self._value:
            if elem.mandatory:
                self._mandatory = True
                return True
        self._mandatory = False
        return False


class OptionalInputElement(InputElementCollection):

    def __repr__(self, verbose=True):
        _repr = "Opt" if verbose else ""
        return _repr + '{' + ", ".join([e.__repr__(verbose=False) for e in self.value]) + '}'


class AlternativeInputElement(InputElementCollection):

    def __repr__(self, verbose=True):
        _repr = "Alt" if verbose else ""
        return _repr + '(' + " | ".join([e.__repr__(verbose=False) for e in self.value]) + ')'

    @property
    def mandatory(self):
        if self._mandatory is not None:
            return self._mandatory
        for elem in self._value:
            if not elem.mandatory:
                self._mandatory = False
                return False
        self._mandatory = True
        return True


class NamedGrammar(InputElementHolder):

    def __init__(self, name, param_list, value):
        super().__init__()
        self._name = name
        self._param_list = []

        if isinstance(value, InputElement):
            self._value = value
        else:
            raise ValueError("Expected InputElement object")

        if not param_list:
            param_list = []

        for param in param_list:
            if not isinstance(param, str):
                raise ValueError("Parameter name should be str not {}".format(type(param)))
            if param in self._param_list:
                raise ValueError("Duplicate parameter name: {}".format(param))
            self._param_list.append(param)

    def copy(self):
        cp = NamedGrammar(self._name, self._param_list, self._value.copy())
        self.copy_extras(cp)
        return cp

    @property
    def param_list(self):
        return self._param_list

    @property
    def value(self):
        return self._value

    @property
    def parent(self):
        return None

    @parent.setter
    def parent(self, p):
        raise ValueError("Cannot set parent for named grammar")

    @property
    def name(self):
        return self._name

    @property
    def mandatory(self):
        return self._value.mandatory


def map_grammar_arguments(grammar_name, parameter_list, arglist):
    arg_count = len(arglist)
    param_list = parameter_list.copy()
    param_count = len(param_list)

    if param_count < arg_count:
        raise ArgumentError(
            "Grammar {} referenced with {} arguments. It has only {} parameters".format(
                grammar_name, arg_count, param_count))

    has_kwarg = False
    param_map = {}

    for arg in arglist:
        if arg.param_name:
            if arg.param_name in param_map:
                raise ArgumentError("Param {} got more than one argument".format(arg.param_name))
            has_kwarg = True
            for param in param_list:
                if arg.param_name == param:
                    param_map[arg.param_name] = arg
                    param_list.remove(param)
                    break
            else:
                raise ArgumentError("Could not match param {} for keyword argument".format(arg.param_name))
        else:
            if has_kwarg:
                raise ArgumentError("Positional argument should not follow keyword argument")
            param = param_list.pop(0)
            param_map[str(param)] = arg

    while param_list:
        param = param_list.pop(0)
        if param.has_def_value:
            param_map[str(param)] = CliArgument(param.defvalue)
        else:
            param_map[str(param)] = CliArgument(None)

    return param_map


class GrammarRefElement(InputElement):

    def __init__(self, grammar, arglist):
        super().__init__()
        if isinstance(grammar, NamedGrammar):
            self._value = grammar
            self._arglist = arglist if arglist else []
            if self._arglist:
                self._param_mapping = map_grammar_arguments(self.name, self._value.param_list, self._arglist)
        else:
            raise ValueError("Expected NamedGrammar object")

    def copy(self):
        cp = GrammarRefElement(self._value, self._arglist)
        self.copy_extras(cp)
        return cp

    @property
    def name(self):
        return self._value.name

    @property
    def value(self):
        return self._value

    @property
    def arg_list(self):
        return self._arglist

    @property
    def param_mapping(self):
        return self._param_mapping

    @property
    def mandatory(self):
        return self._value.mandatory


class UnresolvedInputElement(InputElement):

    def __init__(self, keyword, arglist=None):
        super().__init__()
        if isinstance(keyword, str):
            self._value = keyword
        else:
            raise ValueError("Expected str object")
        self._arglist = arglist if arglist else []

    @property
    def value(self):
        return self._value

    @property
    def arg_list(self):
        return self._arglist

    def copy(self):
        cp = UnresolvedInputElement(self._value)
        self.copy_extras(cp)
        return cp


class TokenClassDef():

    def __init__(self, classname, arglist):
        self._classname = classname
        self._arglist = [arg.value for arg in arglist]

    @property
    def classname(self):
        return self._classname

    @property
    def arglist(self):
        return self._arglist


class GrammarSpecification:

    def __init__(self):
        self._grammars = []
        self._tokens = []
        self._token_defs = {}
        self._named_grammars = {}
        self._unresolved_tokens = {}

    @property
    def grammars(self):
        return self._grammars

    @property
    def tokens(self):
        return self._tokens

    @property
    def token_defs(self):
        return self._token_defs

    @property
    def named_grammars(self):
        return self._named_grammars

    def add_grammar(self, grammar):
        if grammar.name in self._named_grammars:
            raise DuplicateDefinitionException(grammar.name)
        if grammar.name in self._token_defs:
            raise DuplicateDefinitionException(grammar.name)
        self._named_grammars[grammar.name] = grammar
        self._grammars.append(grammar)

    def add_token_def(self, tokenname, classdef):
        if tokenname in self._token_defs:
            raise DuplicateTokendefException(tokenname)
        if tokenname in self._named_grammars:
            raise DuplicateDefinitionException(tokenname)
        self._token_defs[tokenname] = classdef
        self._tokens.append(classdef)

    def add_unresolved_element(self, element):
        if element.value not in self._unresolved_tokens:
            self._unresolved_tokens[element.value] = []
        self._unresolved_tokens[element.value].append(element)

    def get_grammar(self, name):
        if name in self._named_grammars:
            return self._named_grammars[name]
        return None

    def get_tokendef(self, name):
        if name in self.token_defs:
            return self.token_defs[name]
        return None


class LookupToken():

    def __init__(self, node):
        self._lookup_path = {}
        self._node = node
        self._name = self._node.element.value

    @property
    def element(self):
        return self._node.element

    @property
    def node(self):
        return self._node

    @property
    def name(self):
        return self._name

    @property
    def helpstring(self):
        return self._node.element.helpstring

    @property
    def lookup_path(self):
        return self._lookup_path

    def add_lookup_path(self, node, position):
        if not node.path in self._lookup_path:
            self._lookup_path[node.path] = []
        self._lookup_path[node.path].append(position)

    def copy_lookup_path_from(self, previous, node=None):
        if node:
            if node.path in previous.lookup_path:
                self._lookup_path[node.path] = previous.lookup_path[node.path].copy()
            else:
                self._lookup_path[node.path] = []
        else:
            self._lookup_path = previous.lookup_path.copy()

    def path_present(self, node):
        if node.parent.path in self._lookup_path:
            if node.position in self._lookup_path[node.parent.path]:
                return True
        return False

    def next(self):
        nexts = []
        parent = self._node.parent
        position = self._node.position + 1
        end_of_grammar = True

        while parent:
            if not isinstance(parent.element, AlternativeInputElement):
                while True:
                    if isinstance(parent.element, OrderlessSetInputElement):
                        elem = None
                        firsts = []
                        _options = []
                        for i in range(parent.child_count):
                            _elem = parent.get(i)
                            if not self.path_present(_elem):
                                _options.append(_elem)
                                _firsts = _elem.first()
                                for f in _firsts:
                                    f.copy_lookup_path_from(self, parent)
                                    f.add_lookup_path(parent, i)
                                firsts += _firsts
                        if _options and any([o.mandatory for o in _options]):
                            end_of_grammar = False
                    else:
                        if position >= parent.child_count:
                            break
                        elem = parent.get(position)
                        if elem.element.repeat_count > 1:
                            firsts = elem.get(0).first()
                            for f in firsts:
                                f.copy_lookup_path_from(self, parent)
                                f.add_lookup_path(parent, position)
                        else:
                            firsts = elem.first()
                            for f in firsts:
                                f.copy_lookup_path_from(self, parent)
                                f.add_lookup_path(parent, position)

                    temp_parent = parent
                    while temp_parent.parent:
                        for f in firsts:
                            f.copy_lookup_path_from(self, temp_parent.parent)
                            f.add_lookup_path(temp_parent.parent, temp_parent.position)
                        temp_parent = temp_parent.parent

                    nexts += firsts
                    if elem and elem.mandatory:
                        end_of_grammar = False

                    if not end_of_grammar:
                        break
                    position += 1

                    if parent.repeat_count > 1:
                        break

                    if isinstance(parent.element, OrderlessSetInputElement):
                        break

                if not end_of_grammar:
                    break

            position = parent.position + 1

            parent = parent.parent

        if end_of_grammar or not nexts:
            nexts.append(EndOfInpuToken)

        return nexts


class TreeNode():

    def __init__(self, tree, parent, position, element):
        self._parent = parent
        self._tree = tree
        self._path = parent.path + (position,) if parent else (position, )
        self._element = element
        self._children = {}
        self.reset()

    def reset(self):
        self._input_sequence = []
        self._named_vars = {}
        self._numbered_vars = {}
        self._parents = []

    @property
    def child_count(self):
        if isinstance(self._element, InputElementCollection):
            return len(self._element.value) * self._element.repeat_count
        else:
            return 1

    @property
    def parents(self):
        if not self._parents:
            node = self
            while node.parent:
                self._parents.append(node)
                node = node.parent
        return self._parents

    @property
    def tree(self):
        return self._tree

    @property
    def input_sequence(self):
        return self._input_sequence

    @property
    def named_variables(self):
        return self._named_vars

    @property
    def token_variables(self):
        return self._numbered_vars

    @property
    def parent(self):
        return self._parent

    @property
    def element(self):
        return self._element

    @property
    def position(self):
        return self._path[-1]

    @property
    def path(self):
        return self._path

    @property
    def mandatory(self):
        return self._element.mandatory

    @property
    def repeat_count(self):
        return self._element.repeat_count

    def add_named_variable(self, var):
        self._named_vars[var.var_id] = var

    def add_numbered_variable(self, var):
        self._numbered_vars[var.var_id] = var

    def get(self, position):

        if position in self._children:
            return self._children[position]

        if position > 0 and self._element.repeat_count > 1 and position < self._element.repeat_count:
            assert len(self._element.value) == 1
            elem = self._element.value[0].copy()
            elem.parent = self._element
            elem._position = position
            self._children[position] = TreeNode(self.tree, self, position, elem)
        elif isinstance(self._element, InputElementCollection):
            self._children[position] = TreeNode(self.tree, self, position, self._element.value[position])
        elif isinstance(self._element, NamedGrammar) or isinstance(self._element, GrammarRefElement):
            self._children = [TreeNode(self.tree, self, 0, self._element.value)]
        else:
            self._children = [TreeNode(self.tree, self, 0, self._element)]
        return self._children[position]

    def first(self):
        if isinstance(self._element, InputElementCollection):
            firsts = []
            for i in range(self.child_count):
                elem = self.get(i)
                elem_firsts = elem.first()
                for f in elem_firsts:
                    f.add_lookup_path(self, i)
                firsts += elem_firsts

                if isinstance(self.element, AlternativeInputElement) or isinstance(self.element, OrderlessSetInputElement):
                    continue

                if elem.mandatory:
                    break
        elif isinstance(self._element, NamedGrammar) or isinstance(self._element, GrammarRefElement):
            firsts = self.get(0).first()
            for f in firsts:
                f.add_lookup_path(self, 0)
        else:
            firsts = [LookupToken(self)]
        return firsts



class GrammarWalkTree(TreeNode):

    def __init__(self, grammar):
        super().__init__(self, None, 0, grammar)


class _EndOfInpuToken(LookupToken, CliToken):

    __instance = None

    @property
    def completable(self):
        return False

    def get_value(self, match_string=None, cli=None): # noqa
        return NullTokenValue

    @staticmethod
    def getInstance():
        if _EndOfInpuToken.__instance == None:
            _EndOfInpuToken()
        return _EndOfInpuToken.__instance

    def __init__(self):
        if _EndOfInpuToken.__instance != None:
            raise Exception("This class is a singleton!")
        self._hash = hash(_EndOfInpuToken)
        self._name = "$END_OF_INPUT"
        _EndOfInpuToken.__instance = self

    def __repr__(self):
        return "< End of Input >"

    def __str__(self):
        return self.__repr__()

    def __not__(self):
        return True

    def truth(self):
        return False

    def __eq__(self, rhs):
        if isinstance(rhs, _EndOfInpuToken):
            return True
        return False

    def __ne__(self, rhs):
        if isinstance(rhs, _EndOfInpuToken):
            return False
        return True

    def is_(self, rhs):
        if isinstance(rhs, _EndOfInpuToken):
            return True
        return False

    def is_not(self, rhs):
        if isinstance(rhs, _EndOfInpuToken):
            return False
        return True

    def __nonzero__(self):
        return False

    def __bool__(self):
        return False

    def complete(self, token_input=None, cli=None, *args, **kwargs): # noqa
        return []

    def match(self, token_input, cli=None): # noqa
        return MATCH_FAILURE

    @property
    def helpstring(self):
        return str(self)

    @property
    def name(self):
        return self._name

    def next(self):
        return [self]

    def __hash__(self):
        return self._hash


EndOfInpuToken = _EndOfInpuToken.getInstance()
