# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

class BindingCode():

    def __init__(self, block_list):
        self._binding_blocks = block_list

    def __repr__(self):
        return "BindingCode({})".format(self._binding_blocks)

    def __str__(self):
        return self.__repr__()

    @property
    def blocks(self):
        return self._binding_blocks


class AssignmentStatement():

    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = rhs

    def __repr__(self):
        return "AssignmentStatement({} <- {})".format(self._lhs, self._rhs)

    def __str__(self):
        return self.__repr__()

    @property
    def lhs(self):
        return self._lhs

    @property
    def rhs(self):
        return self._rhs


class FunctionCall():

    def __init__(self, name, arglist):
        self._name = name
        self._arglist = arglist

    @property
    def name(self):
        return self._name

    @property
    def arglist(self):
        return self._arglist

    def __repr__(self):
        return "FunctionCall({}, {})".format(self._name, self._arglist)

    def __str__(self):
        return self.__repr__()

class BindingCall(FunctionCall):

    def __repr__(self):
        return "BindingCall({}, {})".format(self._name, self._arglist)

    def __str__(self):
        return self.__repr__()


class BindingStrObject(str):

    def __repr__(self):
        return '"' + self + '"'


class BindingVariable():

    def __init__(self):
        self._value = None

    def assign(self, value):
        if type(self._value) in [NamedVariable, TokenVariable]:
            self._value.assign(value)
        else:
            self._value = value

    @property
    def value(self):
        if type(self._value) in [NamedVariable, TokenVariable]:
            return self._value.value
        return self._value


class NamedVariable(BindingVariable):

    def __init__(self, dollar_name):
        self._name_id = dollar_name
        self._value = None

    def __repr__(self):
        return self._name_id

    def __str__(self):
        return self.__repr__()

    @property
    def var_id(self):
        return self._name_id

    @property
    def var_name(self):
        return self._name_id[1:]


class TokenVariable(BindingVariable):

    def __init__(self, dollar_num):
        self._num_id = dollar_num
        self._value = None

    @property
    def var_id(self):
        return self._num_id

    @property
    def var_index(self):
        return int(self._num_id[1:])

    def __repr__(self):
        return self._num_id

    def __str__(self):
        return self.__repr__()


