# This is an implementation of a trivial router CLI with the nessaid_cli framework
# added for documentation purpose. The step by step making of the CLI is documented as
# inline comments in router_cli_with_inline_comments.py in same folder.
# Follow Step 1: to Step 23:  in that file.

import os
import asyncio
import argparse

from nessaid_cli.cmd import NessaidCmd
from nessaid_cli.tokens import (
    CliToken, StringToken, RangedStringToken, MATCH_SUCCESS, MATCH_PARTIAL, NullTokenValue
)

from nessaid_readline.readkey import readkey

import ipaddress


INTERFACE_MIN_NAME_LEN = 1
INTERFACE_MAX_NAME_LEN = 64


def validate_ip_address(address):
    try:
        ipaddress.ip_address(address)
        return True
    except Exception:
        return False


class InterfaceToken(CliToken):

    def __init__(self, name, cli, helpstring):
        super().__init__(name=name, cli=cli, helpstring=helpstring)

    @property
    def completable(self):
        return True

    @property
    def cacheable(self):
        return False

    async def match(self, input_str, cli):
        options = await cli.get_interface_names()
        m = await CliToken.match_from_multiple(options, input_str, cli=cli)
        if m == MATCH_SUCCESS:
            if input_str in options:
                return MATCH_SUCCESS
            else:
                return MATCH_PARTIAL
        return m

    async def complete(self, input_str, cli):
        options = await cli.get_interface_names()
        return await CliToken.complete_from_multiple(options, input_str, cli=cli)

    async def get_value(self, match_string=None, cli=None):
        options = await cli.get_interface_names()
        if match_string in options:
            return match_string
        return NullTokenValue

    async def get_helpstring(self, match_str, cli=None):
        options = await cli.get_interface_names()
        if match_str and match_str in options:
            return match_str + " - existing interface"
        helpstring = await super().get_helpstring(match_str, cli)
        return helpstring


class InterfaceNameToken(RangedStringToken):

    def __init__(self, name, cli, helpstring):
        super().__init__(name=name, min_len=INTERFACE_MIN_NAME_LEN, max_len=INTERFACE_MAX_NAME_LEN, cli=cli, helpstring=helpstring)

    async def get_helpstring(self, match_str, cli=None): # noqa
        if not self._helpstring:
            return f"Name of the interface: {self._min_len} to {self._max_len} characters"
        return self.helpstring


class IpAddressToken(StringToken):

    def __init__(self, name, cli, helpstring):
        super().__init__(name=name, cli=cli, helpstring=helpstring)

    async def get_helpstring(self, match_str, cli=None): # noqa
        if not self._helpstring:
            return f"An ipv4 or ipv6 address"
        return self.helpstring


class ExistingInterfaceIpAddressToken(CliToken):

    def __init__(self, name, interface_position, helpstring, cli):
        self._interface_position = interface_position
        super().__init__(name, helpstring=helpstring, cli=cli)

    @property
    def completable(self):
        return True

    @property
    def cacheable(self):
        return False

    @property
    def helpstring(self):
        return "An existing local ip address"

    async def get_options(self, cli, s): # noqa
        interfaces = await cli.get_interface_names()
        if self._interface_position is None:
            intf = cli.name
        else:
            matched_values = cli.get_matched_values()
            intf = matched_values[self._interface_position]

        if intf in interfaces:
            return await cli.get_interface_addresses(intf)
        return []

    async def complete(self, s, cli):
        options = await self.get_options(cli, s)
        return await CliToken.complete_from_multiple(options, s, cli)

    async def match(self, s, cli):
        options = await self.get_options(cli, s)
        return await CliToken.match_from_multiple(options, s, cli)

    async def get_value(self, match_string=None, cli=None):
        try:
            n, comp = await self.complete(match_string, cli=cli)
            if n == 1:
                return comp[0]
            elif n > 1:
                if match_string in comp:
                    return match_string
        except:
            pass
        return NullTokenValue


class ConfigInterfaceCmd(NessaidCmd):
    r"""
    token LOCAL_ADDRESS_TOKEN IpAddressToken();
    token EXISTING_ADDRESS_TOKEN ExistingInterfaceIpAddressToken(None);
    """

    def __init__(self, name, *args, **kwargs):
        self._name = name
        self._address = set()
        self._discarded = False
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return self._name

    def get_token_classes(self):
        return [
            IpAddressToken,
            ExistingInterfaceIpAddressToken,
        ]

    async def do_exit(self):
        r"""
        "exit": "Exit from the interface configuration"
        """
        self.exit_loop()

    async def handle_eof(self):
        self.exit_loop()

    async def do_discard(self):
        r"""
        "discard": "Exit from the interface discarding current configuration"
        """
        self._discarded = True
        self.exit_loop()

    async def get_interface_names(self):
        return await self.parent.get_interface_names()

    async def get_interface_addresses(self, name=None):
        name = name or self.name
        return await self.parent.get_interface_addresses(name)

    async def do_address(self, address):
        r"""
        "local-address": "Local address of the interface"
        LOCAL_ADDRESS_TOKEN
        << $address = $2; >>
        """
        if validate_ip_address(address):
            self._address.add(address)
        else:
            print("Invalid IP address:", address, file=self.stdout)

    async def do_no(self, address):
        r"""
        << $interface_name = None; $address = None; >>
        "no": "Remove a config element from this interface"
        (
            "local-address": "Remove a local address"
            EXISTING_ADDRESS_TOKEN
            << $address = $2; >>
        )
        """
        await self.parent.remove_interface(self._name, address)

    async def on_exit(self):
        if not self._discarded:
            await self.parent.configure_interface(name=self._name, address=self._address)


class ConfigCmd(NessaidCmd):
    r"""
    token INTERFACE_NAME_TOKEN InterfaceNameToken();
    token EXISTING_INTERFACE_TOKEN InterfaceToken();
    token EXISTING_INTERFACE_ADDRESS_TOKEN ExistingInterfaceIpAddressToken(2);
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_token_classes(self):
        return [
            InterfaceNameToken,
            InterfaceToken,
            ExistingInterfaceIpAddressToken,
        ]

    async def handle_eof(self):
        self.exit_loop()

    async def get_interface_names(self):
        return await self.parent.get_interface_names()

    async def get_interface_addresses(self, interface):
        return await self.parent.get_interface_addresses(interface)

    async def configure_interface(self, name, address=None):
        await self.parent.configure_interface(name=name, address=address)

    async def remove_interface(self, name, address=None):
        await self.parent.remove_interface(name=name, address=address)

    async def do_end(self):
        r"""
        "end": "Exit from the config shell"
        """
        self.exit_loop()

    async def do_no(self, interface_name, address):
        r"""
        << $interface_name = None; $address = None; >>
        "no": "Remove a config element"
        (
            (
                "interface": "Remove an interface"
                EXISTING_INTERFACE_TOKEN
                << $interface_name = $2; >>
                {
                    "local-address": "Remove a local address"
                    EXISTING_INTERFACE_ADDRESS_TOKEN
                    << $address = $2; >>
                }
            )
        )
        """
        await self.remove_interface(interface_name, address)

    async def do_interface(self, name):
        r"""
        "interface": "Configure an interface"
        (
            INTERFACE_NAME_TOKEN
            << $name = $1; >>
            |
            EXISTING_INTERFACE_TOKEN: "An existing interface"
            << $name = $1; >>
        )
        """
        await self.enter_context(
            ConfigInterfaceCmd,
            name=name,
            use_parent_grammar=False,
            prompt=f"nessaid-router-box: (config/interface/{name}) # ",
            match_parent_grammar=True, disable_default_hooks=True
        )



class ExecCmd(NessaidCmd):
    r"""

    token INTERFACE InterfaceToken();
    token CONFIG_FILE StringToken();

    SHOW_CLI[$section, $interface, $verbose]:
        (
            (
                "system-info": "Show system info"
                << $section = "system-info"; >>
                |
                (
                    "interface": "Show interface info"
                    << $section = "interface-info"; >>
                    {
                        "name": "Name of the specific interface"
                        INTERFACE: "Any of the active interface"
                        << $interface = $2; >>
                    }
                )
                |
                "service": "Show context info"
                << $section = "service-info"; >>
            ),
            {
                "verbose": "Show detailed information"
                << $verbose = True; >>
            }
        )
        ;

    """

    def __init__(self, *args, **kwargs):
        self._interfaces = {
            "local": {'address': {"127.0.0.1"}},
        }
        super().__init__(*args, **kwargs)

    def get_token_classes(self):
        return [
            InterfaceToken, StringToken
        ]

    async def handle_eof(self):
        self.exit_loop()

    async def get_interface_names(self):
        return list(self._interfaces.keys())

    async def get_interface_addresses(self, interface):
        return list(self._interfaces[interface]['address'])

    async def configure_interface(self, name, address=None):
        if name not in self._interfaces:
            self._interfaces[name] = {}
            self._interfaces[name]['address'] = set()
        if address:
            for addr in address:
                self._interfaces[name]['address'].add(addr)

    async def remove_interface(self, name, address=None):
        if name in ['local']:
            if address:
                if address in ['127.0.0.1']:
                    print(f"Cannot remove address {address}", file=self.stdout)
                else:
                    self._interfaces[name]['address'].remove(address)
            else:
                print(f"Cannot remove interface {name}", file=self.stdout)
        else:
            if address:
                self._interfaces[name]['address'].remove(address)
            else:
                del self._interfaces[name]

    async def do_exit(self):
        r"""
        "exit": "Exit from the router-box exec shell"
        |
        "quit": "Exit from the router-box exec shell"
        """
        self.exit_loop()

    async def do_show(self, section, interface, verbose):
        r"""

        << $section = ""; $interface = None; $verbose = False; >>
        "show": "Show various router-box information"
        SHOW_CLI[$section, $interface, $verbose]
        """

        if section == 'interface-info':
            await self.show_interfaces(interface, verbose)
        elif section == 'system-info':
            await self.show_system_info(verbose)
        else:
            print(section, interface, verbose)

    async def show_system_info(self, verbose):
        print("System information", file=self.stdout)
        if verbose:
            print(f"  No details to show", file=self.stdout)

    async def show_service_info(self, verbose):
        print("System information", file=self.stdout)
        if verbose:
            print(f"  No details to show", file=self.stdout)

    async def show_interfaces(self, name, verbose):
        if name:
            interfaces = [name]
        else:
            interfaces = await self.get_interface_names()

        print("Interface information", file=self.stdout)
        for n in interfaces:
            print(f"\n  Name         : {n}", file=self.stdout)
            if self._interfaces[n]:
                if self._interfaces[n]['address']:
                    for addr in sorted(self._interfaces[n]['address']):
                        print(f"    Address    : {addr}", file=self.stdout)
                elif verbose:
                    print(f"    Address    : No addresses configured", file=self.stdout)
            elif verbose:
                print(f"    Details    : No details to show", file=self.stdout)

    async def do_config(self, filename):
        r"""
        "configure": "Configure the box"
        {
            CONFIG_FILE : "Configuration file"
            << $filename = $1; >>
        }
        """

        if filename:
            if os.path.isfile(filename):
                self.add_file_to_execute(filename)
            else:
                self.error("Invalid file")
        else:
            await self.enter_context(
                ConfigCmd,
                use_parent_grammar=False,
                prompt="nessaid-router-box: (config) # ",
                match_parent_grammar=False, disable_default_hooks=True
            )


class LoginPrompt(NessaidCmd):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def do_login(self):
        r"""
        "login": "Login to the router-box"
        """
        await self.login()

    async def do_exit(self):
        r"""
        "exit": "Exit from the router-box shell"
        |
        "quit": "Exit from the router-box shell"
        """
        self.exit_loop()

    async def validate_username(self, username):
        if username == 'admin':
            return True
        return False

    async def validate_password(self, username, password):
        if username == 'admin' and password == 'admin':
            return True
        return False

    async def postintro(self):
        while True:
            status = await self.login()
            if status:
                print("Logged in", file=self.stdout)
                return

    async def login(self):
        username = await self.input("Username: ")
        if not await self.validate_username(username):
            print("Invalid username.", file=self.stdout)
            return False
        password = await self.input("Password: ", show_char=False)
        if not await self.validate_password(username, password):
            print("Invalid password.", file=self.stdout)
            return False

        await self.enter_context(
            ExecCmd,
            use_parent_grammar=False,
            prompt="nessaid-router-box # ",
            match_parent_grammar=False, disable_default_hooks=True
        )
        return True


if __name__ == '__main__':
    intro = "\n" * 3 + "Welcome to nessaid-cli router-box" + "\n" * 2 + "Plese login" + "\n" * 2
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', default=None)
    args = parser.parse_args()

    try:
        LoginPrompt(
            prompt="nessaid-router-box (Not logged in) # ",
            disable_default_hooks=True
        ).run(intro=intro, filename=args.file)
    except Exception as e:
        print("Exception in CLI:", type(e), e)
    readkey()