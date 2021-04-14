# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import unittest


class GrammarTest(unittest.TestCase):

    def test_dummy(self):
        pass

testcase1 = unittest.TestLoader().loadTestsFromTestCase(GrammarTest)

grammar_test = unittest.TestSuite([testcase1])