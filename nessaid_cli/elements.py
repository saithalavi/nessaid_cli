# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

from nessaid_cli.tokens import CliToken, MATCH_FAILURE


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
        while True:
            parent = self.get_parent(level)
            hierarchy.append(parent)
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


class InputElement():

    def __init__(self):
        self._parent = None
        self._value = None
        self._binding = []
        self._pre_exec_binding = None
        self._has_binding = False
        self._position = None
        self._unresolved = False
        self._unresolved_count = 0
        self._has_parenthesis = False
        self._repeat_count = 1

    @property
    def has_repeater(self):
        if self.repeat_count > 1:
            return True
        return False

    @property
    def has_binding_or_repeater(self):
        return self.has_repeater or self.has_binding

    @property
    def repeat_count(self):
        return self._repeat_count

    @repeat_count.setter
    def repeat_count(self, value):
        if isinstance(value, int) and value > 0:
            self._repeat_count = value
        else:
            raise ValueError("Repeater should be > 0")

    def copy_extras(self, cp):
        cp._binding = self._binding
        cp._pre_exec_binding = self._pre_exec_binding
        cp._has_parenthesis = self._has_parenthesis
        cp.repeat_count = self.repeat_count

    def copy(self):
        cp = InputElement()
        self.copy_extras(cp)
        return cp

    def __len__(self):
        return 1

    @property
    def mandatory(self):
        return False

    @property
    def terminal_token(self):
        return True

    @property
    def has_parenthesis(self):
        return self._has_parenthesis

    def __repr__(self):
        if self._parent:
            return "{}".format(self.value)
        return "{}:{}".format(self.__class__.__name__, self.value)

    def __str__(self):
        return self.__repr__()

    @property
    def value(self):
        return self._value

    def __eq__(self, rhs):
        if type(rhs) == self.__class__:
            return self._value == rhs._value
        return False

    def __hash__(self):
        return self._value.__hash__()

    @property
    def parent(self):
        try:
            return self._parent
        except:
            return None

    @parent.setter
    def parent(self, p):
        if not isinstance(p, InputElementCollection):
            raise ValueError("Expected tuple object for parent")
        self._parent = p

    @property
    def position(self):
        if self._position is None:
            if type(self.parent) in [NamedGrammar, GrammarRefElement]:
                self._position = 0
            else:
                self._position = self.parent.index(self)
        return self._position

    @property
    def binding(self):
        try:
            return self._binding
        except:
            return []

    @binding.setter
    def binding(self, b):
        if not isinstance(b, list):
            for e in b:
                if not isinstance(e, str):
                    raise ValueError("Expected str object for binding code")
            raise ValueError("Expected list object for binding code segments")
        self._binding = b

    @property
    def pre_exec_binding(self):
        try:
            if self._pre_exec_binding:
                return self._pre_exec_binding
        except:
            return []

    @pre_exec_binding.setter
    def pre_exec_binding(self, b):
        if not isinstance(b, list):
            for e in b:
                if not isinstance(e, str):
                    raise ValueError("Expected str object for binding code")
            raise ValueError("Expected list object for binding code segments")
        self._pre_exec_binding = b

    @property
    def has_binding(self):
        try:
            return self._has_binding
        except:
            return False

    @has_binding.setter
    def has_binding(self, b):
        if not isinstance(b, bool):
            raise ValueError("Expected boolean object for binding code")
        self._has_binding = b

    @property
    def has_pre_exec_binding(self):
        try:
            if self._pre_exec_binding:
                return True
        except:
            return False

    def handle_brace(self, binding=None):
        t0 = OptionalInputElement((self,))
        if binding:
            t0.pre_exec_binding = binding
            t0.has_binding = True

        self.parent = t0
        t0.has_binding = self.has_binding
        return t0

    def handle_parenthesis(self, binding=None):
        self._has_parenthesis = True
        if binding:
            self.pre_exec_binding = binding + (self.pre_exec_binding if self.pre_exec_binding else [])
            self.has_binding = True
        return self

    def handle_binding(self, binding):
        if binding is not None:
            self.binding.append(binding)
            self.has_binding = True
        return self

    def handle_sequencing(self, t2):
        if not self.has_binding_or_repeater and not t2.has_binding_or_repeater:
            if isinstance(t2, SequenceInputElement):
                first = t2.get(0)
                if not t2.pre_exec_binding or first.mandatory:
                    if t2.pre_exec_binding:
                        first.pre_exec_binding = t2.pre_exec_binding + first.pre_exec_binding
                        t2.pre_exec_binding = []
                    self.parent = t2
                    if self.has_binding:
                        t2.has_binding = True
                    t2._value = (self, ) + t2._value
                    return t2

        t0 = SequenceInputElement((self, t2))
        self.parent = t0
        t2.parent = t0
        if self.has_binding or t2.has_binding:
            t0.has_binding = True
        return t0

    def handle_alternatives(self, t2):
        if isinstance(t2, AlternativeInputElement) and (not t2.has_binding_or_repeater):
            self.parent = t2
            if self.has_binding:
                t2.has_binding = True
            t2._value = tuple(t2.value.union({self}))
            return t2

        t0 = AlternativeInputElement({self, t2})
        self.parent = t0
        t2.parent = t0
        if self.has_binding or t2.has_binding:
            t0.has_binding = True
        return t0


class UnresolvedInputElement(InputElement):

    def __init__(self, keyword, arglist=None):
        super().__init__()
        self._unresolved = True
        self._unresolved_count = 1
        self._arglist = arglist if arglist else []
        if isinstance(keyword, str):
            self._value = keyword
        else:
            raise ValueError("Expected str object")

    @property
    def arg_list(self):
        return self._arglist

    def copy(self):
        cp = UnresolvedInputElement(self._value)
        cp._unresolved = self._unresolved
        cp._unresolved_count = self._unresolved_count
        self.copy_extras(cp)
        return cp

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "unresolved_count": self._unresolved_count,
            "value": self._value,
        }

    @staticmethod
    def from_dict(creator, d):
        elem = UnresolvedInputElement(d["value"])
        elem._unresolved = d["unresolved_count"]
        return elem


class ConstantInputElement(InputElement):

    def __init__(self, keyword):
        super().__init__()
        self._keyword = keyword
        if isinstance(keyword, str):
            if " " in keyword:
                self._value = '"' + keyword + '"'
            else:
                self._value = keyword
        else:
            raise ValueError("Expected str object")

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "value": self._keyword,
        }

    @staticmethod
    def from_dict(creator, d):
        elem = ConstantInputElement(d["value"])
        return elem

    def copy(self):
        cp = ConstantInputElement(self._value)
        cp._value = self._value
        self.copy_extras(cp)
        return cp

    def __hash__(self):
        return self._value.__hash__()

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

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "value": self._value,
        }

    @staticmethod
    def from_dict(creator, d):
        elem = KeywordInputElement(d["value"])
        return elem

    def copy(self):
        cp = KeywordInputElement(self._value)
        self.copy_extras(cp)
        return cp

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


class InputElementCollection(InputElement):

    def __init__(self):
        super().__init__()
        self._value = tuple()

    def __hash__(self):
        return self._value.__hash__()

    def __len__(self):
        return len(self._value)

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

    @property
    def terminal_token(self):
        return False


class SequenceInputElement(InputElementCollection):

    def __init__(self, value):
        super().__init__()
        self._mandatory = None
        if isinstance(value, tuple):
            self._value = value
        else:
            raise ValueError("Expected tuple object")

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "value": [v.as_dict() for v in self._value],
        }

    @staticmethod
    def from_dict(creator, d):
        elem = SequenceInputElement(tuple([creator.dict_to_element(v) for v in d["value"]]))
        return elem

    def __hash__(self):
        return self._value.__hash__()

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

    def copy(self):
        val = tuple([v.copy() for v in self._value])
        cp = SequenceInputElement(val)
        for v in val:
            v.parent = cp
        self.copy_extras(cp)
        return cp

    def __eq__(self, rhs):
        if type(rhs) == self.__class__:
            return self._value == rhs._value
        elif len(self._value) == 1:
            return self._value[0] == rhs
        return False

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

    @property
    def terminal_token(self):
        return False

    def handle_brace(self, binding=None):
        t0 = None
        if not self.has_repeater:
            if all(isinstance(e, OptionalInputElement) for e in self.value):
                t0 = self
                if self.has_pre_exec_binding:
                    binding = self.pre_exec_binding if not binding else binding + self.pre_exec_binding
                    self.pre_exec_binding = []
            else:
                t0 = OptionalInputElement(self.value)
                for e in self.value:
                    e.parent = t0
                    if e.has_binding:
                        t0.has_binding = True

        if t0 is None:
            t0 = OptionalInputElement((self, ))
            self.parent = t0
            t0.has_binding = self.has_binding

        if binding:
            t0.pre_exec_binding = binding
            t0.has_binding = True

        return t0

    def handle_sequencing(self, t2):
        if self.has_binding_or_repeater:
            t0 = SequenceInputElement((self, t2))
            self.parent = t0
            t2.parent = t0
            if self.has_binding or t2.has_binding:
                t0.has_binding = True
        else:
            if not t2.has_binding_or_repeater and isinstance(t2, SequenceInputElement):
                part2 = t2.value
                if t2.pre_exec_binding:
                    first = t2.get(0)
                    first.pre_exec_binding = t2.pre_exec_binding + first.pre_exec_binding
                if t2.binding:
                    last =  t2.get(len(t2) - 1)
                    last.binding = last.binding + t2.binding
            else:
                part2 = (t2,)
                if self.binding:
                    last =  self.get(len(t2) - 1)
                    last.binding = last.binding + self.binding

            for e in part2:
                e.parent = self
                if e.has_binding:
                    self.has_binding = True

            self._value = self._value + part2
            t0 = self

        return t0


class OptionalInputElement(InputElementCollection):

    def __init__(self, value):

        super().__init__()
        if isinstance(value, tuple):
            self._value = value
        else:
            raise ValueError("Expected tuple object")

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "value": [v.as_dict() for v in self._value],
        }

    @staticmethod
    def from_dict(creator, d):
        elem = OptionalInputElement(tuple([creator.dict_to_element(v) for v in d["value"]]))
        return elem

    def copy(self):
        val = tuple([v.copy() for v in self._value])
        cp = OptionalInputElement(val)
        for v in val:
            v.parent = cp
        self.copy_extras(cp)
        return cp

    @property
    def terminal_token(self):
        return False

    def __eq__(self, rhs):
        if type(rhs) == self.__class__:
            return self._value == rhs._value
        return False

    def __hash__(self):
        return self._value.__hash__()

    def __repr__(self):
        rep_str = "{" + ", ".join(str(e) for e in self._value) + "}"
        if self._parent:
            return "{}".format(rep_str)
        return "{}:{}".format(self.__class__.__name__, rep_str)

    def handle_brace(self, binding=None):
        if self.has_repeater:
            t0 = SequenceInputElement((self, ))
            self.parent = t0
            t0.has_binding = self.has_binding
        else:
            t0 = self
            if self.has_pre_exec_binding:
                binding = self.pre_exec_binding if not binding else binding + self.pre_exec_binding
                self.pre_exec_binding = []

        if binding:
            t0.pre_exec_binding = binding
            t0.has_binding = True

        return t0

    def handle_alternatives(self, t2):
        part1 = None
        part2 = None

        if not (self.has_binding_or_repeater or t2.has_binding_or_repeater):
            if (len(self) == 1):
                if isinstance(self.value[0], AlternativeInputElement):
                    part1 = self.value[0].value
                else:
                    part1 = {self.value[0]}

            if type(t2) == AlternativeInputElement:
                part2 = t2.value
            elif (len(t2) == 1):
                if isinstance(t2.value[0], AlternativeInputElement):
                    part2 = t2.value[0].value
                else:
                    part2 = {t2}

            if (part1 is not None) and (part2 is not None):
                alt = AlternativeInputElement(part1.union(part2))
                for c in alt.value:
                    c.parent = alt
                t0 = OptionalInputElement((alt, ))
                alt.parent = t0
                return t0

        t0 = AlternativeInputElement({self, t2})
        self.parent = t0
        t2.parent = t0
        if self.has_binding or t2.has_binding:
            t0.has_binding = True
        return t0


class AlternativeInputElement(InputElementCollection):

    def __init__(self, value):

        super().__init__()
        self._mandatory = None
        if isinstance(value, set):
            self._value = tuple(value)
        else:
            raise ValueError("Expected set object")

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "value": [v.as_dict() for v in self._value],
        }

    @staticmethod
    def from_dict(creator, d):
        elem = AlternativeInputElement(set([creator.dict_to_element(v) for v in d["value"]]))
        return elem

    def copy(self):
        val = set([v.copy() for v in self._value])
        cp = AlternativeInputElement(val)
        for v in val:
            v.parent = cp
        self.copy_extras(cp)
        return cp

    def __eq__(self, rhs):
        if type(rhs) == self.__class__:
            return self._value == rhs._value
        elif (len(self) == 1) and (rhs in self._value):
            return True
        return False

    def __hash__(self):
        return self._value.__hash__()

    @property
    def terminal_token(self):
        if not  self._value:
            return False
        for e in self._value:
            if e.terminal_token is False:
                return False
        return True

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

    @property
    def value(self):
        return set(self._value)

    def __repr__(self):
        rep_str = "(" + " | ".join(str(e) for e in self._value) + ")"
        if self._parent:
            return "{}".format(rep_str)
        return "{}:{}".format(self.__class__.__name__, rep_str)

    def handle_alternatives(self, t2):

        if type(t2) == OptionalInputElement:
            return t2.handle_alternatives(self)

        if not (self.has_binding_or_repeater or t2.has_binding_or_repeater):
            if isinstance(t2, AlternativeInputElement):
                part2 = t2.value
            else:
                part2 = {t2,}

            for e in part2:
                e.parent = self
            if e.has_binding:
                self.has_binding = True

            self._value = tuple(self.value.union(part2))
            return self

        t0 = AlternativeInputElement({self, t2})
        self.parent = t0
        t2.parent = t0
        if self.has_binding or t2.has_binding:
            t0.has_binding = True
        return t0

    def first(self, root_grammar=None):
        firsts = []
        for i in self._value:
            firsts += i.first(root_grammar=root_grammar)
        if self.parent:
            for first in firsts:
                first.add_prefix(self.position)
        return firsts


class NamedGrammar(InputElementCollection):

    def __init__(self, name, param_list, value):
        super().__init__()
        self._name = name
        self._param_list = param_list if param_list else []

        validated_params = []

        for param in self._param_list:
            if not isinstance(param, str):
                raise ValueError("Parameter name should be str not {}".format(type(param)))
            if param in validated_params:
                raise ValueError("Duplicate parameter name: {}".format(param))
            validated_params.append(param)

        if isinstance(value, InputElement):
            self._value = value
            value.parent = self
        else:
            raise ValueError("Expected InputElement object")

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "name": self._name,
            "value": self._value.as_dict(),
            "param_list": self._param_list,
        }

    @staticmethod
    def from_dict(creator, d):
        elem = NamedGrammar(d["name"], d["param_list"], creator.dict_to_element(d["value"]))
        return elem

    def copy(self):
        cp = NamedGrammar(self._name, self._param_list, self._value.copy())
        self.copy_extras(cp)
        return cp

    @property
    def terminal_token(self):
        return self._value.terminal_token

    @property
    def param_list(self):
        return self._param_list

    @property
    def value(self):
        return self._value.value

    def get(self, position):
        if position == 0:
            return self._value
        raise IndexError("NamedGrammar: Invalid index: {}".format(position))

    def index(self, child):
        if self._value == child:
            return 0
        raise IndexError("{} doesnt have {}".format(self, child))

    @property
    def parent(self):
        return None

    @property
    def mandatory(self):
        return self._value.mandatory

    @parent.setter
    def parent(self, p):
        raise ValueError("Cannot set parent for named grammar")

    @property
    def position(self):
        return 0

    @property
    def name(self):
        return self._name

    def __eq__(self, rhs):
        if type(rhs) == self.__class__:
            return self._value == rhs._value
        return False

    def __len__(self):
        return 1

    def __hash__(self):
        return self._value.__hash__()

    def first(self, root_grammar=None):
        firsts = self._value.first(root_grammar=root_grammar)
        for first in firsts:
            first.add_prefix(self.position)
        return firsts

    def __repr__(self):
        return "NamedGrammar({}:{})".format(self._name, self._value.__repr__())


class GrammarRefElement(InputElement):

    def __init__(self, grammar, arglist):
        super().__init__()
        if isinstance(grammar, NamedGrammar):
            self._name = grammar.name
            self._value = grammar
            self._arglist = arglist if arglist else []
            if self._arglist:
                arg_count = len(self._arglist)
                param_list = grammar.param_list
                param_count = len(param_list)
                if param_count < arg_count:
                    raise ValueError(
                        "Grammar {} referenced with {} arguments. It has only {} parameters".format(
                            self._name, arg_count, param_count))
        else:
            raise ValueError("Expected NamedGrammar object")

    def as_dict(self):
        return {
            "classname": self.__class__.__name__,
            "name": self._name,
            "arglist": self._arglist,
        }

    @staticmethod
    def from_dict(creator, d):
        grammar = creator.get_grammar(d["name"])
        elem = GrammarRefElement(grammar, d["arglist"])
        return elem

    def copy(self):
        cp = GrammarRefElement(self._value, self._arglist)
        self.copy_extras(cp)
        return cp

    @property
    def value(self):
        return self._value.value

    @property
    def terminal_token(self):
        return self._value.terminal_token

    @property
    def arg_list(self):
        return self._arglist

    def __eq__(self, rhs):
        if type(rhs) == self.__class__:
            return self._value == rhs._value
        return False

    def __hash__(self):
        return self._value.__hash__()

    def __repr__(self):
        return "GrammarRef({}:{})".format(self._name, self._value._value.__repr__())

    def get(self, position):
        if position == 0:
            return self._value
        raise IndexError("GrammarRefElement: Invalid index: {}".format(position))

    def first(self, root_grammar=None):
        firsts = self._value.first(root_grammar=root_grammar)
        if self.parent:
            for first in firsts:
                first.add_prefix(self.position)
        return firsts

    @property
    def mandatory(self):
        return self._value.mandatory


class ElementTreeCreator():

    element_map = None

    element_classes = [
        UnresolvedInputElement,
        ConstantInputElement,
        KeywordInputElement,
        SequenceInputElement,
        OptionalInputElement,
        AlternativeInputElement,
        NamedGrammar,
        GrammarRefElement,
    ]

    def __init__(self, json_dict):
        self._json_dict = json_dict
        self._token_map = {}
        self._grammar_map = {}
        if ElementTreeCreator.element_map is None:
            ElementTreeCreator.element_map = {e.__name__: e for e in ElementTreeCreator.element_classes}

    def get_grammar(self, name):
        return self._grammar_map[name]

    def dict_to_element(self, d):
        elem_class = ElementTreeCreator.element_classes[d['name']]
        obj = elem_class.from_dict(self, d)
        if isinstance(obj, NamedGrammar):
            self._grammar_map[d['name']] = obj

    def get_grammars(self):
        return {}

    def get_token_defs(self):
        return {}
