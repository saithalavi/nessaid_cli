# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.tokens import CliToken, MATCH_FAILURE
from nessaid_cli.lex_yacc_common import DollarVariable
from nessaid_cli.utils import ExtendedString


class CliParameter(ExtendedString):

    def __init__(self, value, defvalue=None, has_def_value=False):
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


class TokenHierarchyElement():

    def __init__(self, element, path):
        self._element = element
        self._path = tuple(path)
        self._named_vars = {}
        self._numbered_vars = {}
        self._input_sequence = []

    @property
    def named_variables(self):
        return self._named_vars

    @property
    def token_variables(self):
        return self._numbered_vars

    @property
    def input_sequence(self):
        return self._input_sequence

    @property
    def element(self):
        return self._element

    def add_named_variable(self, var):
        self._named_vars[var.var_id] = var

    def add_numbered_variable(self, var):
        self._numbered_vars[var.var_id] = var

    @property
    def path(self):
        return self._path

    def __eq__(self, rhs):
        if isinstance(rhs, TokenHierarchyElement):
            return (self._element == rhs._element) and (self._path == rhs.path)
        return False

    def __hash__(self):
        return hash(self._element) + hash(self._path)


class TokenLookup():

    def __init__(self, token, root_grammar=None):
        self.token = token
        self.path = []
        self._root_grammar = root_grammar
        self._parent_stack = []

    @property
    def name(self):
        return self.token.value

    def add_prefix(self, prefix):
        self.path = [prefix] + self.path

    def get_element_hierarchy(self):
        self._parent_stack = []
        hierarchy = []
        level = 0
        parent_path = self.path.copy()
        while True:
            parent = self.get_parent(level)
            hierarchy.append(TokenHierarchyElement(parent, parent_path.copy()))
            parent_path.pop()
            level += 1
            if parent is self._root_grammar:
                self._parent_stack = []
                return hierarchy

    def __eq__(self, rhs):
        if isinstance(rhs, TokenLookup):
            if self._root_grammar is rhs._root_grammar:
                if (self.token == rhs.token) and (self.path == rhs.path):
                    return True
        return False

    def __hash__(self):
        return hash(self.token) + hash(tuple(self.path))

    def __repr__(self):
        return "{}:<{}>".format(self.token, ",".join(str(p) for p in self.path))

    def _locate(self, path):
        parent = self._root_grammar

        while path:
            position = path.pop(0)
            parent = parent.get(position)
        return parent

    def get_parent(self, parent_level):
        """
        R  P2  P1 T
        0  p2  p1 pt
        """
        if not self._parent_stack:
            level = 0
            parent = self.token

            self._parent_stack.append(parent)
            level += 1

            while parent:
                if type(parent) in [NamedGrammar]:
                    parent = self._locate(self.path[1:][:-level])
                else:
                    parent = parent.parent
                self._parent_stack.append(parent)
                if parent is self._root_grammar:
                    break
                level += 1

        return self._parent_stack[parent_level]


    def next(self):
        nexts = []
        self._parent_stack = []
        # import pdb; pdb.set_trace()
        level = 0
        parent = self.get_parent(level + 1)
        level += 1
        position = self.token.position + 1
        end_of_grammar = True

        while parent:
            elem = None
            if not isinstance(parent, AlternativeInputElement):
                while position < len(parent):
                    elem = parent.get(position)
                    if elem.repeat_count > 1:
                        firsts = elem.get(0).first(root_grammar=self._root_grammar)
                        for f in firsts:
                            f.add_prefix(elem.position)
                    else:
                        firsts = elem.first(root_grammar=self._root_grammar)

                    temp_parent = parent
                    temp_level = level

                    while temp_parent:
                        for f in firsts:
                            f.add_prefix(temp_parent.position)
                        if temp_parent is self._root_grammar:
                            break
                        temp_parent = self.get_parent(temp_level + 1)
                        temp_level += 1

                    nexts += firsts
                    if elem.mandatory:
                        end_of_grammar = False
                        break
                    position += 1

                    if parent.repeat_count > 1:
                        break
                if elem and elem.mandatory:
                    break

            if parent is self._root_grammar:
                break
            position = parent.position + 1
            parent = self.get_parent(level + 1)
            level += 1

        if end_of_grammar or not nexts:
            nexts.append(EndOfInpuToken())

        self._parent_stack = []
        return nexts


class _EndOfInpuToken(TokenLookup, CliToken):

    __instance = None

    @property
    def completable(self):
        return False

    def get_value(self, match_string=None):
        return None

    @staticmethod
    def getInstance():
        if _EndOfInpuToken.__instance == None:
            _EndOfInpuToken()
        return _EndOfInpuToken.__instance

    def __init__(self):
        if _EndOfInpuToken.__instance != None:
            raise Exception("This class is a singleton!")
        self._name = "$END_OF_INPUT"
        _EndOfInpuToken.__instance = self

    def __repr__(self):
        return "< End of Input >"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, rhs):
        if isinstance(rhs, _EndOfInpuToken):
            return True
        return False

    def __hash__(self):
        return hash(self._name)

    def __not__(self):
        return True

    def truth(self):
        return False

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

    def complete(self, *args, **kwargs):
        return []

    def match(self, token_input):
        return MATCH_FAILURE

    @property
    def helpstring(self):
        return str(self)

    @property
    def name(self):
        return self._name

    def next(self):
        return [self]


def EndOfInpuToken():
    return _EndOfInpuToken.getInstance()


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

    def __init__(self):
        self._parent = None
        self._value = None
        self._pre_match_binding = []
        self._post_match_binding = []
        self._position = None
        self._repeat_count = 1

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

    @property
    def position(self):
        if self._position is None:
            if type(self.parent) in [NamedGrammar, GrammarRefElement]:
                self._position = 0
            else:
                self._position = self.parent.index(self)
        return self._position

    @position.setter
    def position(self, pos):
        pos = int(pos)
        if pos < 0:
            raise ValueError("Position should be 0 or a positive integer")
        self._position = pos

    def validate_binding(self, b):
        if not isinstance(b, list):
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


class ConstantInputElement(InputElement):

    def __init__(self, keyword):
        super().__init__()
        self._value = keyword

    def copy(self):
        cp = ConstantInputElement(self._value)
        self.copy_extras(cp)
        return cp

    def __repr__(self, verbose=True):
        return self._value

    @property
    def mandatory(self):
        return True

    def first(self, root_grammar=None):
        first =  TokenLookup(self, root_grammar=root_grammar)
        if self.parent:
            first.add_prefix(self.position)
        return [first]


class KeywordInputElement(InputElement):

    def __init__(self, keyword):
        super().__init__()
        if isinstance(keyword, str):
            self._value = keyword
        else:
            raise ValueError("Expected str object")

    def copy(self):
        cp = KeywordInputElement(self._value)
        self.copy_extras(cp)
        return cp

    def __repr__(self, verbose=True):
        return self._value

    def __hash__(self):
        return self._value.__hash__()

    @property
    def mandatory(self):
        return True

    def first(self, root_grammar=None):
        first = TokenLookup(self, root_grammar=root_grammar)
        if self.parent:
            first.add_prefix(self.position)
        return [first]


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

    def get(self, position):
        return self._value[position]

    def index(self, child):
        pos = 0
        for c in self._value:
            if id(c) == id(child):
                return pos
            pos += 1
        raise IndexError("{} doesnt have {}".format(self, child))

    def first(self, root_grammar=None):
        firsts = []
        for i in range(len(self)):
            elem = self.get(i)
            firsts += elem.first(root_grammar=root_grammar)
            if elem.mandatory:
                break

        if self.parent:
            for first in firsts:
                first.add_prefix(self.position)
        return firsts


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

    def get(self, position):
        if position > 0 and self.repeat_count > 1 and position < self.repeat_count:
            assert len(self._value) == 1
            elem = self._value[0].copy()
            elem.parent = self
            elem._position = position
            return elem
        return self._value[position]

    def index(self, child):
        if self.repeat_count > 1 and child.position < self.repeat_count:
            if child.parent == self:
                if child.position < len(self):
                    return child.position
        pos = 0
        for c in self._value:
            if id(c) == id(child):
                return pos
            pos += 1
        raise IndexError("{} doesnt have {}".format(self, child))

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

    def first(self, root_grammar=None):
        firsts = []
        for i in self._value:
            firsts += i.first(root_grammar=root_grammar)
        if self.parent:
            for first in firsts:
                first.add_prefix(self.position)
        return firsts


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

    def get(self, position):
        if position == 0:
            return self._value
        raise IndexError("NamedGrammar: Invalid index: {}".format(position))

    def index(self, child):
        if id(self._value) == id(child):
            return 0
        raise IndexError("{} doesnt have {}".format(self, child))

    @property
    def parent(self):
        return None

    @parent.setter
    def parent(self, p):
        raise ValueError("Cannot set parent for named grammar")

    @property
    def position(self):
        return 0

    @property
    def name(self):
        return self._name

    @property
    def mandatory(self):
        return self._value.mandatory

    def first(self, root_grammar=None):
        firsts = self._value.first(root_grammar=root_grammar)
        for first in firsts:
            first.add_prefix(self.position)
        return firsts


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

    def get(self, position):
        if position == 0:
            return self._value
        raise IndexError("GrammarRefElement: Invalid index: {}".format(position))

    @property
    def mandatory(self):
        return self._value.mandatory

    def first(self, root_grammar=None):
        firsts = self._value.first(root_grammar=root_grammar)
        if self.parent:
            for first in firsts:
                first.add_prefix(self.position)
        return firsts


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