# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

import os
import time
import asyncio
import traceback

from nessaid_cli.elements import EndOfInpuToken
from nessaid_cli.interface import CliInterface, TokenCompletion
from nessaid_cli.tokens import MATCH_SUCCESS, MATCH_PARTIAL, MATCH_AMBIGUOUS
from nessaid_cli.tokenizer.tokenizer import NessaidCliTokenizer, TokenizerException

import nessaid_readline.key as key
from nessaid_readline.async_readline import NessaidAsyncReadline, NessaidReadlineEOF, NessaidReadlineKeyboadInterrupt


class ChildCliExitException(Exception):

    def __init__(self, tok_list, dry_run=False, last_token_complete=False, arglist=None):
        self.token_list = tok_list
        self.dry_run = dry_run
        self.last_token_complete = last_token_complete
        self.arglist = arglist


class CliAlreadyRunning(Exception):
    pass


class ParentBackup():

    def __init__(self, cli, readline):
        self._cli = cli
        self._parent = cli.parent
        self._readline = readline
        self._enable_bell = readline._enable_bell

    async def restore(self):
        self._readline.set_prepare_history_entry(lambda entry: entry.strip())
        self._readline.set_history_size(self._parent._history_size)
        self._readline.enable_bell(self._enable_bell)
        self._parent._exec_inited = False
        await self._parent.cli_exec_init()

class NessaidCli(CliInterface):

    def __init__(self, grammarset, loop=None, parent=None,
                 prompt=None, stdin=None, stdout=None, stderr=None, filename=None,
                 completekey='tab', use_rawinput=True, history_size=100, enable_bell=False, str_cache_size=128):

        self._loop = loop if loop else asyncio.get_event_loop()
        self.validate_token_classes()

        super().__init__(self._loop, grammarset, stdin=stdin, stdout=stdout, stderr=stderr, str_cache_size=str_cache_size)

        enable_bell = False if enable_bell is not True else True

        self._history_size = history_size

        if not parent:
            self._readline = NessaidAsyncReadline(loop=self.loop, stdin=self.stdin, stdout=self.stdout, stderr=self.stderr)
            self._readline.set_prepare_history_entry(lambda entry: entry.strip())
            self._readline.set_history_size(self._history_size)
        else:
            self._parent_backup = ParentBackup(self, parent.readline)
            self._readline = parent.readline

        self._readline.enable_bell(enable_bell)

        self._complete_tokens_processor =  self.process_completion_tokens

        self._filename = filename
        self._parent = parent
        self._completekey = completekey
        self._use_rawinput = use_rawinput
        self._completion_matches = []
        self._exit_loop = False
        self._exec_inited = False
        self._current_line = None
        self._prompt = "" if not prompt else prompt
        self._empty_line_matching = False
        self._suggestion_shown = False
        self._waiting_input = False
        self._nessaid_tokenizer = NessaidCliTokenizer()

        self._child_cli = None
        self._running = False
        self._loop_task = None

        if parent:
            self._cli_stack = parent._cli_stack
        else:
            self._cli_stack = []
        self._file_data = []
        self._partial_line = False
        self._effective_line = ""

    @property
    def loop(self):
        return self._loop

    @property
    def parent(self):
        return self._parent

    @property
    def parent_backup(self):
        return self._parent_backup

    @property
    def file_data(self):
        if self.parent:
            return self.parent.file_data
        return self._file_data

    @property
    def file_line(self):
        if self.parent:
            return self.parent.file_line
        if self._file_data:
            file_content = self._file_data[-1]
            if file_content:
                file_line = file_content.pop(0)
                if not file_content:
                    self._file_data.pop()
                return file_line
        return None

    @property
    def prompt(self):
        return self._prompt

    @property
    def child_cli(self):
        return self._child_cli

    @child_cli.setter
    def child_cli(self, cli):
        self._child_cli = cli

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, running):
        self._running = True if running else False

    def validate_token_classes(self):
        token_classes = self.get_token_classes()
        for cls in token_classes:
            methods = [cls.complete, cls.match, cls.get_value]
            if (all([asyncio.iscoroutinefunction(m) for m in methods]) or
                all([not asyncio.iscoroutinefunction(m) for m in methods])):
                pass
            else:
                msg = ("WARNING: A mix of async and non async functions are used for " +
                       "the match, complete, get_value mthods of class {}.\nThis will most probably " +
                       "end up in failures as these functions call one another\n").format(cls.__name__)
                print(msg, file=self.stderr)

    @property
    def readline(self):
        return self._readline

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

    async def get_next_line(self, prompt, show_prompt_for_file_lines=True, from_stdin=False):

        line = None if from_stdin else self.file_line
        if line is not None:
            if show_prompt_for_file_lines:
                self.print(prompt, end="")
            self.print(line)
            return line

        try:
            line = await self.readline.readline(prompt)
        except EOFError:
            line = ""

        return line

    async def complete(self, text, state): #noqa

        if self._waiting_input:
            await self._readline.insert_text("\t")
            return None

        if self._partial_line:

            line = self._readline.get_line_buffer()
            current_line = self._effective_line or ""
            current_line += line

            while self._readline.get_line_buffer():
                await self._readline.insert_text(key.BACKSPACE)
            await self._readline.insert_text(current_line)
            self._partial_line = False
            self._effective_line = ""
            self._readline._input_prompt = self.prompt
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

            match_output = await self.match(input_tokens, dry_run=True, last_token_complete=last_token_complete)

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
            if match_output.next_tokens and EndOfInpuToken in match_output.next_tokens:
                match_output.next_tokens.remove(EndOfInpuToken)
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
                                await self._readline.insert_text(tok_replacement[replace_len:])
                                self._suggestion_shown = False
                                return None
                            elif self._suggestion_shown and self._current_line and len(line) > len(self._current_line):
                                if cli_startswith(line, self._current_line):
                                    idx = line.rindex(tok_input)
                                    replace_len = len(line) - idx
                                    await self._readline.insert_text(tok_replacement[replace_len:])
                                    if len(completions) == 1 and completions[0] == tok_replacement:
                                        await self._readline.insert_text(DEFAULT_SEPARATOR)
                                    self._suggestion_shown = False
                                    return None
                        elif match_output.next_constant_token and match_output.next_constant_token == tok_input:
                            if line and line[-1] not in TOKEN_SEPARATORS:
                                await self._readline.insert_text(DEFAULT_SEPARATOR)
                                self._suggestion_shown = False
                                return None
                elif match_output.next_constant_token:
                    if line and line[-1] in TOKEN_SEPARATORS:
                        if line == self._current_line:
                            await self._readline.insert_text(match_output.next_constant_token)
                            self._suggestion_shown = False
                            return None
                    elif not line and self._empty_line_matching:
                        self._empty_line_matching = False
                        await self._readline.insert_text(match_output.next_constant_token)
                        self._suggestion_shown = False
                        return None
            else:
                self.set_completion_tokens(["Failed to parse: {}".format(match_output.error)])
                self._readline.play_bell()
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

    def process_completion_tokens(self, tokens):
        comps = []
        helps = []
        completions = []
        add_completion_token = False

        if "NEWLINE: Complete command" in tokens:
            tokens.remove("NEWLINE: Complete command")
            add_completion_token = True
            if not tokens:
                return ["NEWLINE: Complete command"]

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
        if add_completion_token:
            max_len = min(max(max_len, len('NEWLINE')), 40)

        for i in range(len(comps)):
            comp = comps[i]
            if len(comp) <= max_len:
                comp += " " * (max_len - len(comp))
            if helps[i]:
                comp += (" :    " + helps[i])
            completions.append(comp)

        completions = sorted(completions)

        if add_completion_token:
            comp = 'NEWLINE'
            if len(comp) <= max_len:
                comp += " " * (max_len - len(comp))
                comp += (" :    " + "Complete command")
                completions.append(comp)

        return completions

    def set_completion_tokens(self, tokens):
        self._completion_matches = self._complete_tokens_processor(tokens)

    async def input(self, prompt="", show_char=True, show_prompt_for_file_lines=True, from_stdin=False):

        try:
            self._waiting_input = True
            line = None if from_stdin else self.file_line
            if line is not None:
                if show_prompt_for_file_lines:
                    self.print(prompt, end="")
                if show_char:
                    self.print(line)
                else:
                    self.print("*" * len(line))
                return line
            return await self._readline.input(prompt, mask_input=not show_char)
        except Exception:
            return ""
        finally:
            self._waiting_input = False

    async def preloop(self):
        pass

    async def postintro(self):
        pass

    def exit_loop(self):
        """Exit thr running Cli loop"""
        self._exit_loop = True

    def exec_args(self, *args):
        line = " ".join(args)
        return self.loop.run_until_complete(self.exec_line(line))

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
            return 11

        try:
            arglist = []
            input_tokens = [str(t) for t in tokens]
            match_output = await self.match(input_tokens, dry_run=False, last_token_complete=True, arglist=arglist)
            self.process_cli_response(tokens, match_output)
            if match_output.result == MATCH_SUCCESS:
                return 0
            return 12
        except Exception as e:
            self.error("Exception parsing input line:", type(e), e)
            self.error("\n")
            traceback.print_tb(e.__traceback__, file=self.stderr)
            self.error("\n")
            return 13

    async def cli_exec_init(self):
        if not self._exec_inited:
            self._readline.set_completer(self.complete)
            self._readline.parse_and_bind(self._completekey+": complete")
            self._exec_inited = True

    async def context_loop(self):
        raise NotImplementedError

    async def handle_keyboard_interrupt(self):
        pass

    async def handle_eof(self):
        pass

    def add_file_to_execute(self, filename):
        try:
            with open(filename) as fd:
                lines = [l.rstrip() for l in fd.readlines()]
                self.file_data.append(lines)
        except Exception as e:
            self.error("Exception processing input file:", filename, type(e), e)

    async def is_partial_line(self, line):
        try:
            if line.rstrip().endswith("\\"):
                return True, line.rstrip()[:-1]
        except Exception as e:
            pass
        return False, line

    async def commented_line(self, line):
        try:
            if line.lstrip().startswith("#"):
                return True
        except Exception as e:
            pass
        return False

    async def cmdloop(self, grammarname, intro=None):

        if self._filename:
            self.add_file_to_execute(self._filename)

        self._running = True
        self._cli_stack.append(self)
        self.enter_grammar(grammarname)

        try:
            await self.preloop()
            await self.cli_exec_init()
            if intro is not None:
                self.stdout.write(str(intro)+"\n")
                self.stdout.flush()

            self._child_cli = None

            await self.postintro()

            while self.child_cli:
                child_cli = self.child_cli
                try:
                    await child_cli.context_loop()
                except ChildCliExitException as e:
                    match_output = await self.match(
                        e.token_list, dry_run=e.dry_run,
                        last_token_complete=e.last_token_complete, arglist=e.arglist
                    )
                finally:
                    self.child_cli = None

            self._partial_line = False
            self._effective_line = ""

            while not self._exit_loop:

                try:
                    if self._partial_line:
                        line = await self.get_next_line("")
                    else:
                        line = await self.get_next_line(self.prompt)
                except NessaidReadlineKeyboadInterrupt:
                    await self.handle_keyboard_interrupt()
                    continue
                except NessaidReadlineEOF:
                    await self.handle_eof()
                    continue

                self._effective_line += line
                self._partial_line, self._effective_line = await self.is_partial_line(self._effective_line)

                if self._partial_line:
                    continue

                self._partial_line = False

                if await self.commented_line(self._effective_line):
                    self._effective_line = ""
                    continue

                self._current_line = self._effective_line
                self._effective_line = ""

                try:
                    success, error, tokens = self.tokenize(self._current_line)
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
                    self.child_cli = None
                    match_output = await self.match(input_tokens, dry_run=False, last_token_complete=True, arglist=arglist)

                    while self._child_cli:
                        child_cli = self.child_cli
                        try:
                            await child_cli.context_loop()
                            self.child_cli = None
                        except ChildCliExitException as e:
                            self.child_cli = None
                            match_output = await self.match(e.token_list, dry_run=False, last_token_complete=True, arglist=arglist)
                        finally:
                            pass

                    self._current_line = None
                    self.process_cli_response(tokens, match_output)
                except ChildCliExitException as e:
                    raise e
                except Exception as e:
                    self.error("Exception parsing input line:", type(e), e)
                    self.error("\n")
                    traceback.print_tb(e.__traceback__, file=self.stderr)
                    self.error("\n")
        finally:
            await self.on_exit()
            self._exit_loop = False
            self.exit_grammar()
            self._running = False
            top_cli = self._cli_stack.pop()
            if self != top_cli:
                raise(Exception("Bug in CLI stack"))
            self._loop_task = None

    async def on_exit(self):
        pass

    def process_cli_response(self, tokens, cli_response):
        if tokens and cli_response.result != MATCH_SUCCESS:
            self.error("Result:", cli_response.result)
            self.error("Error:", cli_response.error)
            self._readline.play_bell()

    async def monitor_loop(self):
        while self._running:
            await asyncio.sleep(.5)

    def handle_external_keyboard_interrupt(self):
        if self.child_cli:
            self.child_cli.handle_external_keyboard_interrupt()
        else:
            self._readline.handle_external_keyboard_interrupt()

    def run(self, grammarname, intro=None):
        if self.running:
            raise CliAlreadyRunning("Cli is running")

        self.running = True
        loop = self.loop or asyncio.get_event_loop()
        self._loop_task = loop.create_task(self.cmdloop(grammarname=grammarname, intro=intro))

        if not loop.is_running():
            mon_task = self.loop.create_task(self.monitor_loop())
            while self.running:
                try:
                    loop.run_until_complete(mon_task)
                    time.sleep(.1)
                    break
                except KeyboardInterrupt:
                    while True:
                        try:
                            self.handle_external_keyboard_interrupt()
                        except KeyboardInterrupt:
                            continue
                        else:
                            break