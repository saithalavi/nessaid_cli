# Defining custom tokens

This write-up will show how to define custom tokens for the CLI. The steps are.
* Define our token class
* import it to our Cli or Cmd class file
* Override the class's get_token_classes method so as to return all the token classes used for the CLI
* define the tokens in the grammar

## The token class
The token class should extend the CliToken class which is available in tokens.py. Then we can override the following methods to define the behavior of the token
* helpstring: proprty method. Will suggest the token's description to the CLI, unless there are auto-completable choices for the token
* completable: proprty method. Returns True if the token can be auto-completed.
* complete: method accepts the current cli input, which can be a part of the next token, or an empty string. It returns a tuple (n, l) where n is the number of matching choices constructible from the input part and l is the list of completions. If we have too many completions possible we may return (TOO_MANY_COMPLETIONS, []). We should implement this method if completable returns True.
* match: method accepts the current input part for the token. Returns MATCH_SUCCESS if it's a match. Returns MATCH_PARTIAL if the token can be matched with extra input or the current input can be auto-completed. Returns MATCH_FAILURE if current input cannot be matched to this token.
* get_value: accepts the current input part for the token. Returns the possible token value from the input. If the input can't be matched with the token, return None.

## Example classes

### AlternativeStringsToken
This class accepts a list or sequence of strings as possible matches. It matches the input with the members of the list, considering auto-completion.
```python
class AlternativeStringsToken(CliToken):

    def __init__(self, name, alternatives, *args):
        super().__init__(name)
        if (isinstance(alternatives, list) or
            isinstance(alternatives, set) or
            isinstance(alternatives, tuple)):
            self._alternatives = list(alternatives)
        elif args:
            self._alternatives = [alternatives] + list(args)
        else:
            self._alternatives = []

    @property
    def helpstring(self):
        return "Any one of: {}".format(set(self._alternatives))

    @property
    def completable(self):
        return True

    def complete(self, token_input):
        if not token_input:
            return len(self._alternatives), list(self._alternatives)
        completions = set()
        for e in self._alternatives:
            if token_input and e.startswith(token_input):
                completions.add(e)
        return len(completions), list(completions)

    def match(self, token_input):
        if token_input and token_input in  self._alternatives:
            return MATCH_SUCCESS
        n, completions = self.complete(token_input)
        if n == TOO_MANY_COMPLETIONS:
            return MATCH_PARTIAL
        if not completions:
            return MATCH_FAILURE
        elif len(completions) == 1:
            return MATCH_SUCCESS
        else:
            return MATCH_PARTIAL
```

### RangedDecimalToken
This class will process decimal numbers within specified range. For obvious reasons, we cannot autocomplete them whereas it is possible for integer tokens.
```python
class RangedDecimalToken(CliToken):

    def __init__(self, name, start, end):
        start = float(start)
        end = float(end)
        super().__init__(name)
        self._start = min(start, end)
        self._end = max(start, end)

    @property
    def helpstring(self):
        return "A decimal number between {} and {}".format(self._start, self._end)

    @property
    def completable(self):
        return False

    def complete(self, token_input):
        return 0, []

    def match(self, token_input):
        if isinstance(token_input, str):
            if token_input == "":
                return MATCH_PARTIAL
            if token_input == "-":
                if self._start >= 0 :
                    return MATCH_FAILURE
                return MATCH_PARTIAL
            try:
                decimal = float(token_input)
            except Exception:
                return MATCH_FAILURE
            if decimal > 0 and decimal > self._end:
                return MATCH_FAILURE
            if decimal < 0 and decimal < self._start:
                return MATCH_FAILURE
            return MATCH_PARTIAL
        return MATCH_FAILURE

    def get_value(self, match_string=None):
        try:
            number = float(match_string)
            if number >= self._start and number <= self._end:
                return number
        except Exception:
            pass
        return None
```

## Further examples
More token class examples are available in tokens.py of the package.
