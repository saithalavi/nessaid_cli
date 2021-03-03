import unittest


class GrammarTest(unittest.TestCase):

    def test_dummy(self):
        pass

testcase1 = unittest.TestLoader().loadTestsFromTestCase(GrammarTest)

grammar_test = unittest.TestSuite([testcase1])