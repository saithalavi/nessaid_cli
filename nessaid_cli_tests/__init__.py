# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import unittest


from nessaid_cli_tests.test_tokenizer import tokenizer_test
from nessaid_cli_tests.test_cli import cli_test
from nessaid_cli_tests.test_grammar import grammar_test


def doTests():
  print('Started Nessaid Cli Python implementation testing.\n')
  unittest.TextTestRunner(verbosity=2).run(tokenizer_test)
  unittest.TextTestRunner(verbosity=2).run(cli_test)
  unittest.TextTestRunner(verbosity=2).run(grammar_test)