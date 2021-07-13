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

from nessaid_cli.elements import EndOfInpuToken
from nessaid_cli.interface import CliInterface, ParsingResult
from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer, TokenizerException
from nessaid_cli.tokens import CliToken, MATCH_SUCCESS, MATCH_PARTIAL, MATCH_AMBIGUOUS


try:
    import curses
    CURSES_KEY_BACKSPACE = curses.KEY_BACKSPACE
except:
    CURSES_KEY_BACKSPACE = 263

try:
    import getch
    def getinput(prompt, show_char=False):
        """Replacement for getpass.getpass() which prints asterisks for each character typed"""
        print(prompt, end='', flush=True)

        buf = ''
        kbd_int = False
        while True:
            try:
                try:
                    ch = getch.getch()
                except KeyboardInterrupt:
                    buf = ""
                    kbd_int = True
                    break
                except OverflowError as e:
                    continue
            except KeyboardInterrupt:
                buf = ""
                kbd_int = True
                break
            except OverflowError as e:
                continue

            if ch == '\n':
                print('')
                break
            elif ch in (CURSES_KEY_BACKSPACE, '\b', '\x7f'):
                if len(buf) > 0:
                    buf = buf[:-1]
                    print('\b', end='', flush=True)
                    print(" ", end='', flush=True)
                    print('\b', end='', flush=True)
            else:
                buf += ch
                c = '*' if show_char is False else ch
                print(c, end='', flush=True)
        if kbd_int:
            print("\n", end='', flush=True)
        return buf

except ImportError:
    import getpass as gp

    def getinput(prompt, show_char=True):
        if show_char:
            return input(prompt)

        return gp.getpass(prompt)


class NessaidCli(CliInterface):

    def __init__(self, grammarset, loop=None, prompt=None,
                 stdin=None, stdout=None, stderr=None, completekey='tab', use_rawinput=True):

        super().__init__(loop, grammarset, stdin=stdin, stdout=stdout, stderr=stderr)

        self._match_loop = asyncio.new_event_loop()

        self._completekey = completekey
        self._use_rawinput = use_rawinput
        self._cmdqueue = []
        self._old_completer = None
        self._completion_matches = []
        self._exit_loop = False
        self._exec_inited = False
        self._current_line = None
        self._prompt = "" if not prompt else prompt
        self._empty_line_matching = False
        self._suggestion_shown = False
        self._waiting_input = False

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

            try:
                tokens = self._nessaid_tokenizer.parse(line)
                return True, None, tokens
            except TokenizerException as e:
                return False, "Invalid input: {}".format(line), []
        except Exception as e:
            return False, "Exception parsing line: {}: {}".format(type(e), e)

    async def get_next_line(self, prompt):
        if self._cmdqueue:
            line = self._cmdqueue.pop(0)
        elif self._use_rawinput:
            try:
                line = await self.loop.run_in_executor(None, input, prompt)
            except EOFError:
                line = ""
        else:

            def _readline():
                self.stdout.write(prompt)
                self.stdout.flush()
                line = self.stdin.readline()
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

        if self._waiting_input:
            readline.insert_text("\t")
            return None

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
            success, error, tokens = self.tokenize(line)
            if not success:
                self.set_completion_tokens(["Failure tokenizing input line: {}".format(line)])
                return self._completion_matches[state]
        except Exception as e:
            self.set_completion_tokens(["Exception tokenizing input line: {}: {}".format(type(e), e)])
            return None

        if line and line[-1] in TOKEN_SEPARATORS:
            last_token_complete = True
        else:
            last_token_complete = False

        try:
            input_tokens = [str(t) for t in tokens]

            match_output = self._match_loop.run_until_complete(
                    self.match(input_tokens, dry_run=True, last_token_complete=last_token_complete)
                )

            completions = []

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
                                idx = line.rindex(tok_input)
                                replace_len = len(line) - idx
                                readline.insert_text(tok_replacement[replace_len:])
                                self._suggestion_shown = False
                                return None
                            elif self._suggestion_shown and self._current_line and len(line) > len(self._current_line):
                                if cli_startswith(line, self._current_line):
                                    idx = line.rindex(tok_input)
                                    replace_len = len(line) - idx
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
            self.set_completion_tokens(["Exception matchinsinput line: {}: {}".format(type(e), e)])
            return self._completion_matches[state]

        return None

    def process_completions(self, status, completions):
        pass

    def set_completion_tokens(self, tokens):
        """
        comp_tokens = []
        char_repl_maps = {
            "\\": "\\\\",
            "\n": "\\n",
            "\t": "\\t",
            '"': '\\"'
        }
        for tok in tokens:
            if tok.startswith('"'):
                comp_token = tok[1:]
                if tok.endswith('"'):
                    comp_token = comp_token[:-1]
                    e = '"'
                else:
                    e = ""
                for r, repl in char_repl_maps.items():
                    comp_token = comp_token.replace(r, repl)
                comp_tokens.append('"' + comp_token + e)
            else:
                comp_tokens.append(tok)
                """
        comp_tokens = tokens
        if len(comp_tokens) > 1:
            if os.name == 'nt':
                comp_tokens = sorted(comp_tokens)
                comp_tokens = [comp_tokens[0]] + ['\n' + t for t in comp_tokens[1:]]
        self._completion_matches = comp_tokens + [" "]

    def input(self, prompt="", show_char=True):

        try:
            self._waiting_input = True
            return getinput(prompt, show_char)
        except Exception:
            return ""
        finally:
            self._waiting_input = False

    async def get_input(self, prompt="", show_char=True):

        try:
            self._waiting_input = True
            return await self.loop.run_in_executor(None, getinput, prompt, show_char)
        except Exception:
            return ""
        finally:
            self._waiting_input = False

    async def preloop(self):
        pass

    def exit_loop(self):
        """Exit thr running Cli loop"""
        self._exit_loop = True

    async def exec_args(self, *args):
        line = " ".join(args)
        return await self.exec_line(line)

    async def exec_line(self, line):
        try:
            success, error, tokens = self.tokenize(line)
            if not success:
                self.error("Failure tokenizing input line:", error)
        except Exception as e:
            self.error("Exception tokenizing input line:", type(e), e)
            self.error("\n")
            traceback.print_tb(e.__traceback__, file=self.stderr)
            self.error("\n")

        try:
            arglist = []
            input_tokens = [str(t) for t in tokens]
            match_output = await self.match(input_tokens, dry_run=False, last_token_complete=True, arglist=arglist)
            self.process_cli_response(tokens, match_output)
        except Exception as e:
            self.error("Exception parsing input line:", type(e), e)
            self.error("\n")
            traceback.print_tb(e.__traceback__, file=self.stderr)
            self.error("\n")

    async def cli_exec_init(self):
        if not self._exec_inited:
            if self._use_rawinput and self._completekey:
                self._old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                if readline.__doc__ and 'libedit' in readline.__doc__:
                    readline.parse_and_bind("bind ^I rl_complete")
                else:
                  readline.parse_and_bind(self._completekey+": complete")
            self._exec_inited = True

    async def cmdloop(self, grammarname, intro=None):
        self.enter_grammar(grammarname)
        try:
            await self.preloop()
            await self.cli_exec_init()
            if intro is not None:
                self.stdout.write(str(intro)+"\n")
                self.stdout.flush()

            while not self._exit_loop:
                line = await self.get_next_line(self.prompt)
                self._current_line = line
                #print("Input:", line)
                try:
                    success, error, tokens = self.tokenize(line)
                    if not success:
                        self.error("Failure tokenizing input line:", error)
                except Exception as e:
                    self.error("Exception tokenizing input line:", type(e), e)
                    self.error("\n")
                    traceback.print_tb(e.__traceback__, file=self.stderr)
                    self.error("\n")
                else:
                    #print("Tokens:", tokens)
                    pass

                try:
                    arglist = []
                    input_tokens = [str(t) for t in tokens]
                    match_output = await self.match(input_tokens, dry_run=False, last_token_complete=True, arglist=arglist)
                    self._current_line = None
                    self.process_cli_response(tokens, match_output)
                except Exception as e:
                    self.error("Exception parsing input line:", type(e), e)
                    self.error("\n")
                    traceback.print_tb(e.__traceback__, file=self.stderr)
                    self.error("\n")
        finally:
            self.exit_grammar()

    def process_cli_response(self, tokens, cli_response):
        if tokens and cli_response.result != MATCH_SUCCESS:
            self.error("Result:", cli_response.result)
            self.error("Error:", cli_response.error)
