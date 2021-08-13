# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import os
import asyncio
import traceback

from nessaid_cli.elements import EndOfInpuToken
from nessaid_cli.interface import CliInterface, TokenCompletion
from nessaid_cli.tokens import MATCH_SUCCESS, MATCH_PARTIAL, MATCH_AMBIGUOUS
from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer, TokenizerException
from nessaid_readline.readline import NessaidReadline, NessaidReadlineEOF, NessaidReadlineKeyboadInterrupt


class NessaidCli(CliInterface):

    def __init__(self, grammarset, loop=None, prompt=None,
                 stdin=None, stdout=None, stderr=None,
                 completekey='tab', use_rawinput=True, use_readline=False,
                 history_size=100):

        super().__init__(loop, grammarset, stdin=stdin, stdout=stdout, stderr=stderr)

        self._cli_readline = NessaidReadline()
        self._history_size = history_size

        if use_readline is True:
            import readline
            self._readline = readline
            self._read_input = input
            self._complete_tokens_processor = self.process_completion_tokens_for_readline
        else:
            self._readline = self.get_readline()
            self._read_input = self._readline.readline
            self._complete_tokens_processor =  self.process_completion_tokens
            self._readline.set_prepare_history_entry(lambda entry: entry.strip())
            self._readline.set_history_size(self._history_size)

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

    def __del__(self):
        try:
            self._match_loop.close()
        except:
            pass

    @property
    def loop(self):
        return self._loop

    @property
    def prompt(self):
        return self._prompt

    def get_readline(self):
        return self._cli_readline

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
                line = await self.loop.run_in_executor(None, self._read_input, prompt)
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

    def complete(self, text, state): #noqa

        if self._waiting_input:
            self._readline.insert_text("\t")
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

        line = self._readline.get_line_buffer()

        try:
            success, error, tokens = self.tokenize(line)
            if not success:
                self.set_completion_tokens(["Failure tokenizing input line: {} error: {}".format(line, error)])
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
                                self._readline.insert_text(tok_replacement[replace_len:])
                                self._suggestion_shown = False
                                return None
                            elif self._suggestion_shown and self._current_line and len(line) > len(self._current_line):
                                if cli_startswith(line, self._current_line):
                                    idx = line.rindex(tok_input)
                                    replace_len = len(line) - idx
                                    self._readline.insert_text(tok_replacement[replace_len:])
                                    if len(completions) == 1 and completions[0] == tok_replacement:
                                        self._readline.insert_text(DEFAULT_SEPARATOR)
                                    self._suggestion_shown = False
                                    return None
                        elif match_output.next_constant_token and match_output.next_constant_token == tok_input:
                            if line and line[-1] not in TOKEN_SEPARATORS:
                                self._readline.insert_text(DEFAULT_SEPARATOR)
                                self._suggestion_shown = False
                                return None
                elif match_output.next_constant_token:
                    if line and line[-1] in TOKEN_SEPARATORS:
                        if line == self._current_line:
                            self._readline.insert_text(match_output.next_constant_token)
                            self._suggestion_shown = False
                            return None
                    elif not line and self._empty_line_matching:
                        self._empty_line_matching = False
                        self._readline.insert_text(match_output.next_constant_token)
                        self._suggestion_shown = False
                        return None
            else:
                self.set_completion_tokens(["Failed to parse: {}".format(match_output.error)])
                self._cli_readline.play_bell()
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

    def process_completion_tokens_for_readline(self, tokens):
        comp_tokens = tokens
        if len(comp_tokens) > 1:
            if os.name == 'nt':
                comp_tokens = sorted(comp_tokens)
                comp_tokens = [comp_tokens[0]] + ['\n' + t for t in comp_tokens[1:]]
        return comp_tokens

    def process_completion_tokens(self, tokens):
        comps = []
        helps = []
        completions = []

        for t in tokens:
            if isinstance(t, TokenCompletion):
                if not t.completion:
                    comps.append("")
                else:
                    comps.append(t.completion)
                helps.append(t.helpstring)
            else:
                comps.append(str(t))
                helps.append("")

        max_len = min(max([len(c) for c in comps]), 40)
        for i in range(len(comps)):
            comp = comps[i]
            if len(comp) <= max_len:
                comp += " " * (max_len - len(comp))
            if helps[i]:
                comp += (" :    " + helps[i])
            completions.append(comp)

        completions = sorted(completions)
        return completions

    def set_completion_tokens(self, tokens):
        self._completion_matches = self._complete_tokens_processor(tokens)

    def input(self, prompt="", show_char=True):

        try:
            self._waiting_input = True
            return self._readline.input(prompt, mask_input=not show_char)
        except Exception:
            return ""
        finally:
            self._waiting_input = False

    async def get_input(self, prompt="", show_char=True):

        try:
            self._waiting_input = True
            return await self.loop.run_in_executor(None, self._readline.input, prompt, mask_input=not show_char)
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
                self._old_completer = self._readline.get_completer()
                self._readline.set_completer(self.complete)
                if self._readline.__doc__ and 'libedit' in self._readline.__doc__:
                    self._readline.parse_and_bind("bind ^I rl_complete")
                else:
                    self._readline.parse_and_bind(self._completekey+": complete")
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
                try:
                    line = await self.get_next_line(self.prompt)
                except NessaidReadlineKeyboadInterrupt:
                    continue
                except NessaidReadlineEOF:
                    self._exit_loop = True
                    continue
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
            self._cli_readline.play_bell()

    def run(self, grammarname, intro=None):
        loop = self.loop or asyncio.get_event_loop()
        if loop.is_running:
            loop.create_task(self.cmdloop(grammarname=grammarname, intro=intro))
        else:
            loop.run_until_complete(self.cmdloop(grammarname=grammarname, intro=intro))