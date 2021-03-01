# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import os
import sys
import asyncio
import readline
import traceback
import platform
import rlcompleter

from nessaid_cli.interface import CliInterface
from nessaid_cli.elements import EndOfInpuToken
from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer
from nessaid_cli.tokens import CliToken, MATCH_SUCCESS, MATCH_PARTIAL, MATCH_AMBIGUOUS


class NessaidCli(CliInterface):

    def __init__(self, grammarset, loop=None, prompt=None,
                 stdin=None, stdout=None, stderr=None, completekey='tab', use_rawinput=True):

        if stdin is not None:
            self._stdin = stdin
        else:
            self._stdin = sys.stdin

        if stdout is not None:
            self._stdout = stdout
        else:
            self._stdout = sys.stdout

        if stderr is not None:
            self._stderr = stderr
        else:
            self._stderr = sys.stderr

        super().__init__(grammarset)

        self._completekey = completekey
        self._use_rawinput = use_rawinput
        self._cmdqueue = []
        self._old_completer = None
        self._completion_matches = []
        self._exit_loop = False
        self._current_line = None
        self._prompt = "" if not prompt else prompt
        self._empty_line_matching = False
        self._suggestion_shown = False

        self._loop = loop if loop else asyncio.get_event_loop()
        self._nessaid_tokenizer = NessaidCliTokenizer()

    @property
    def loop(self):
        return self._loop

    @property
    def prompt(self):
        return self._prompt

    def tokenize(self, line):
        try:
            if line == '\n':
                line = ""
            return self._nessaid_tokenizer.parse(line)
        except Exception as e:
            print("Exception parsing line:", type(e), e)
            return []

    async def get_next_line(self):
        if self._cmdqueue:
            line = self._cmdqueue.pop(0)
        elif self._use_rawinput:
            try:
                line = await self.loop.run_in_executor(None, input, self.prompt)
            except EOFError:
                line = ""
        else:

            def _readline():
                self._stdout.write(self.prompt)
                self._stdout.flush()
                line = self._stdin.readline()
                if not len(line):
                    line = ""
                else:
                    line = line.rstrip('\r\n')
                return line

            try:
                line = await self.loop.run_in_executor(None, _readline)
            except Exception:
                line = ""

        return line

    def complete(self, text, state):

        TOKEN_SEPARATORS = [" "]
        DEFAULT_SEPARATOR = " "

        if state != 0:
            try:
                if self._completion_matches and len(self._completion_matches) > state:
                    return self._completion_matches[state]
                else:
                    return None
            except IndexError:
                return None

        line = readline.get_line_buffer()

        try:
            tokens = self.tokenize(line)
            # print("tokens:", tokens)
        except Exception as e:
            print("Exception tokenizing input line:", type(e), e)
            return None

        if line and line[-1] in TOKEN_SEPARATORS:
            last_token_complete = True
        else:
            last_token_complete = False

        try:
            match_output = self.match(tokens, dry_run=True, last_token_complete=last_token_complete)
            completions = []

            def cli_rindex(string, substring):
                try:
                    return string.rindex(substring), 0
                except Exception:
                    if match_output.case_insensitive:
                        string = string.lower()
                        substring = substring.lower()
                    n = substring.count("\\")
                    return string.rindex(substring.replace("\\", "\\\\")), n

            def cli_startswith(string, substring):
                if string.startswith(substring):
                    return True
                else:
                    if match_output.case_insensitive:
                        if string.lower().startswith(substring.lower()):
                            return True
                return False

            has_full_match = False
            if match_output.next_tokens and EndOfInpuToken() in match_output.next_tokens:
                match_output.next_tokens.remove(EndOfInpuToken())
                has_full_match = True

            if match_output.result == MATCH_SUCCESS:
                completions += ["NEWLINE: Complete command"]
            elif match_output.result in [MATCH_PARTIAL, MATCH_AMBIGUOUS]:
                completions = match_output.next_tokens
                if has_full_match:
                    completions += ["NEWLINE: Complete command"]
                if match_output.last_token:
                    tok_input = match_output.last_token[0]
                    tok_replacement = match_output.last_token[1]
                    if tok_replacement and cli_startswith(tok_replacement, tok_input):
                        if tok_input != tok_replacement:
                            if line == self._current_line:
                                idx, reps = cli_rindex(line, tok_input)
                                replace_len = len(line) - idx - reps
                                readline.insert_text(tok_replacement[replace_len:])
                                self._suggestion_shown = False
                                return None
                            elif self._suggestion_shown and self._current_line and len(line) > len(self._current_line):
                                if cli_startswith(line, self._current_line):
                                    idx, reps = cli_rindex(line, tok_input)
                                    replace_len = len(line) - idx - reps
                                    readline.insert_text(tok_replacement[replace_len:])
                                    if len(completions) == 1 and completions[0] == tok_replacement:
                                        readline.insert_text(DEFAULT_SEPARATOR)
                                    self._suggestion_shown = False
                                    return None
                        elif match_output.next_constant_token and match_output.next_constant_token == tok_input:
                            if line and line[-1] not in TOKEN_SEPARATORS:
                                readline.insert_text(DEFAULT_SEPARATOR)
                                self._suggestion_shown = False
                                return None
                elif match_output.next_constant_token:
                    if line and line[-1] in TOKEN_SEPARATORS:
                        if line == self._current_line:
                            readline.insert_text(match_output.next_constant_token)
                            self._suggestion_shown = False
                            return None
                    elif not line and self._empty_line_matching:
                        self._empty_line_matching = False
                        readline.insert_text(match_output.next_constant_token)
                        self._suggestion_shown = False
                        return None
            else:
                self.set_completion_tokens(["Failed to parse: {}".format(match_output.error)])
                return self._completion_matches[state]

            self.set_completion_tokens(completions)
            if completions and match_output.last_token:
                self._suggestion_shown = True

            if not line:
                self._empty_line_matching = True
            else:
                self._empty_line_matching = False
            self._current_line = line

            return self._completion_matches[state]

        except Exception as e:
            print("Exception matchin input line:", type(e), e)
            return None

        return None

    def process_completions(self, status, completions):
        pass

    def set_completion_tokens(self, tokens):
        if len(tokens) > 1:
            if os.name == 'nt':
                tokens = sorted(tokens)
                tokens = [tokens[0]] + ['\n' + t for t in tokens[1:]]
        self._completion_matches = tokens + [" "]

    async def preloop(self):
        pass

    def exit_loop(self):
        """Exit thr running Cli loop"""
        self._exit_loop = True

    async def cmdloop(self, grammarname, intro=None):
        self.enter_grammar(grammarname)
        try:
            await self.preloop()

            if self._use_rawinput and self._completekey:
                self._old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                if readline.__doc__ and 'libedit' in readline.__doc__:
                    readline.parse_and_bind("bind ^I rl_complete")
                else:
                  readline.parse_and_bind(self._completekey+": complete")

            if intro is not None:
                self._stdout.write(str(intro)+"\n")

            while not self._exit_loop:
                line = await self.get_next_line()
                self._current_line = line
                #print("Input:", line)
                try:
                    tokens = self.tokenize(line)
                except Exception as e:
                    print("Exception tokenizing input line:", type(e), e)
                    print("\n")
                    traceback.print_tb(e.__traceback__)
                    print("\n")
                else:
                    #print("Tokens:", tokens)
                    pass

                try:
                    arglist = [1, 1.5, "nessaid_cli"]
                    match_output = self.match(tokens, dry_run=False, last_token_complete=True, arglist=arglist)
                    self._current_line = None
                    self.process_cli_response(tokens, match_output)
                except Exception as e:
                    print("Exception parsing input line:", type(e), e)
                    print("\n")
                    traceback.print_tb(e.__traceback__)
                    print("\n")
        finally:
            self.exit_grammar()

    def process_cli_response(self, tokens, cli_response):
        if tokens and cli_response.result != MATCH_SUCCESS:
            print("Result:", cli_response.result)
            print("Error:", cli_response.error)
