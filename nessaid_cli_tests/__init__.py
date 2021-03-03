import unittest


from nessaid_cli_tests.test_cli import cli_test
from nessaid_cli_tests.test_grammar import grammar_test


def doTests():
  print('Started Nessaid Cli Python implementation testing.\n')
  unittest.TextTestRunner(verbosity=2).run(cli_test)
  unittest.TextTestRunner(verbosity=2).run(grammar_test)