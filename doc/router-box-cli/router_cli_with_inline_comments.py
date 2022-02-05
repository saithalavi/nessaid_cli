from nessaid_cli.cmd import NessaidCmd
from nessaid_cli.tokens import CliToken, StringToken, RangedStringToken, NullTokenValue

import ipaddress


INTERFACE_MIN_NAME_LEN = 1
INTERFACE_MAX_NAME_LEN = 64


def validate_ip_address(address):
    try:
        ipaddress.ip_address(address)
        return True
    except:
        return False


# Step 18: Token class definition for InterfaceToken. It helps to auto complete already
#          available interfaces
class InterfaceToken(CliToken):

    # Step 19: Define the token class members. Base class is CliToken in nessaid_cli/tokens.py
    #          Refer the examples in that folder

    # __init__ accpets name followed by user defined parameters if any(Taken from CLI definitions) followed by
    # the cli object and helpstring for the token if any
    def __init__(self, name, cli, helpstring):
        super().__init__(name=name, cli=cli, helpstring=helpstring)

    # For tokens capable of auto completion, this propery should be True
    @property
    def completable(self):
        return True

    # match will accept the complete or partial token input and cli. It should return any of
    # [MATCH_SUCCESS, MATCH_FAILURE, MATCH_PARTIAL]
    async def match(self, input_str, cli):
        options = await cli.get_interface_names()
        return await CliToken.match_from_multiple(options, input_str, cli=cli)

    # Complete should return a tuple of the number of valid inputs that can be created from theinput string
    # and the list of completions
    # If too many completions are possible, it should return (TOO_MANY_COMPLETIONS, [])
    async def complete(self, input_str, cli):
        options = await cli.get_interface_names()
        return await CliToken.complete_from_multiple(options, input_str, cli=cli)

    # get valuse should return the complet keyword/option generated from the input
    async def get_value(self, match_string=None, cli=None):
        n, comp = await self.complete(match_string, cli)
        if n == 1:
            return comp[0]
        elif n > 1:
            if match_string in comp:
                    return match_string
        return NullTokenValue

    # If a helpstring was given from CLI definition that will take precedence
    async def get_helpstring(self, match_str, cli=None):
        if match_str:
            return match_str
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

    # Step 23: The Cli definition below has the following token definition
    #          token EXISTING_INTERFACE_TOKEN ExistingInterfaceIpAddressToken(2);
    #          the argument 2 will be set right after the token name by the framework
    #          for the time being keyword arguments are not supported, soon it will be added
    #          The 2 here means the index of the token to be looked for getting the interface name
    #          We can use the index to find the interface name by getting the list of tokens already matched
    #          For example, the address deletion CLI, when parsing the address token will have the following
    #          tokens matched
    #          'no' 'interface' <interface-name> 'local-address'
    #          So we take the token at 2nd index to get the list of addresses available in that interface
    #          This helps us to match addresses in any interface
    def __init__(self, name, interface_position, helpstring, cli):
        self._interface_position = interface_position
        super().__init__(name, helpstring=helpstring, cli=cli)

    @property
    def completable(self):
        return True

    @property
    def helpstring(self):
        return "An existing local ip address"

    async def get_options(self, cli, s): # noqa
        # The following returns the list of current tokens, in completed form
        matched_values = cli.get_matched_values()
        interfaces = await cli.get_interface_names()
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
    """

    def __init__(self, name, *args, **kwargs):
        self._name = name
        self._address = set()
        self._discarded = False
        super().__init__(*args, **kwargs)

    def get_token_classes(self):
        return [
            IpAddressToken,
        ]

    async def do_exit(self):
        r"""
        "exit": "Exit from the interface configuration"
        """
        self.exit_loop()

    async def do_discard(self):
        r"""
        "discard": "Exit from the interface discarding current configuration"
        """
        self._discarded = True
        self.exit_loop()

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

    async def on_exit(self):
        if not self._discarded:
            await self.parent.configure_interface(name=self._name, address=self._address)


class ConfigCmd(NessaidCmd):
    r"""
    token INTERFACE_NAME_TOKEN InterfaceNameToken();
    token REMOVE_INTERFACE_TOKEN InterfaceToken();
    # Step 22: This is how we define a custom token with parameter. Here the parameter 2 will be available in the token class
    token EXISTING_INTERFACE_TOKEN ExistingInterfaceIpAddressToken(2);
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_token_classes(self):
        return [
            InterfaceNameToken,
            InterfaceToken,
            ExistingInterfaceIpAddressToken,
        ]

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
                REMOVE_INTERFACE_TOKEN
                << $interface_name = $2; >>
                {
                    "local-address": "Remove a local address"
                    # Step 21: Define the token for available addresses in an interface
                    # Note step 22 and step 23
                    EXISTING_INTERFACE_TOKEN
                    << $address = $2; >>
                }
            )
        )
        """
        await self.remove_interface(interface_name, address)

    async def do_interface(self, name):
        r"""
        "interface": "Configure an interface"
        INTERFACE_NAME_TOKEN
        << $name = $2; >>
        """
        await self.enter_context(
            ConfigInterfaceCmd,
            name=name,
            use_parent_grammar=False,
            prompt=f"nessaid-router-box: (config/interface/{name}) # ",
            match_parent_grammar=True, disable_default_hooks=True
        )



# Step 9: Compose the CLI class for exec commands. The exec commands to be implemented are
#         'configure', 'show', 'exit' and 'quit'
class ExecCmd(NessaidCmd):
    r"""

    # Step 17: The INTERFACE token maps to the InterfaceToken class without any extra parameters. By default token
    #          class instances will be invoked with (name, *args, cli=cli, helpstring=helpstring_from_token_reference)
    #           we should fill *args in the token definition
    token INTERFACE InterfaceToken();

    # Step 14: The CLI definition for the follow up for 'show' token. It sets the values
    #          of incoming variables as per input, so that it can be available to the calling CLI
    #          grammar and then to the python hook

    SHOW_CLI[$section, $interface, $verbose]:
        # The show token should follow with some mandatory token combinations
        ( # This parenthesis covers the mandatory follow up section of show it's a set containing 2 sections
            # Section 1 of the set: The following parenthesis mandates selection of system-info, interface, or service
            # The optional section 2 is after the comma
            (
                # We should show one among system-info, interface, or service
                "system-info": "Show system info"
                << $section = "system-info"; >>
                |
                (
                    "interface": "Show interface info"
                    << $section = "interface-info"; >>
                    {
                        "name": "Name of the specific interface"
                        # Step 16: Define the INTERFACE token
                        INTERFACE: "Any of the active interface"
                        << $interface = $2; >>
                    }
                )
                |
                "service": "Show context info"
                << $section = "service-info"; >>
            ),
            # This section is optional, but as the parent block is a set, it can be matched before or after the mandatory sibling block
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
            InterfaceToken,
        ]

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

    # Step 10: Compose the show CLI
    async def do_show(self, section, interface, verbose):
        r"""

        # Step 12: The function parameters will be automatically initialized in CLI as empty strings
        #          here if we didn't set the values explicitly, all the variables will have  '' as
        #          value unless the following CLI sets them based on input

        << $section = ""; $interface = None; $verbose = False; >>

        # Step 11: This CLI options start with the token 'show'. We can add the helpstring right after the
        # token preceded by a colon. The helpstring will be shown to prompt for this command


        "show": "Show various router-box information"

        # This is the call to the grammar definition for show CLI. The grammar definitions are included
        # in the class's docstring. The definitions in the function docstrings are the ones that will trigger
        # the function.

        # Step 13: Here this CLI doesn't set the values, but passes them to SHOW_CLI definition.
        #          there the values will be set based on input

        SHOW_CLI[$section, $interface, $verbose]
        """

        # Step 15: Once the CLI specification above matched, the variables will be set and will be available to
        #          python code. $verbose in CLI corresponds to verbose in python

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

    # Step 20: Spawn a config sub cli context when 'config' is matched
    async def do_config(self):
        r"""
        "configure": "Configure the box"
        """
        await self.enter_context(
            ConfigCmd,
            use_parent_grammar=False,
            prompt="nessaid-router-box: (config) # ",
            match_parent_grammar=False, disable_default_hooks=True
        )


# Step 4: Define the initial CLI class. It doesnt have any global grammar, so no __doc__ for the class
class LoginPrompt(NessaidCmd):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Step 6: Define the login command. After login, the actual CLI sessions can exit back to this
    #         CLI so we need to relogin from here
    async def do_login(self):
        r"""
        "login": "Login to the router-box"
        """
        await self.login()

    # Step 7: Define the exit command. This CLI can exit to OS shell on matching
    #         either 'exit' or 'quit'
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

    # Called before the actual CLI loop starts.
    async def preloop(self):
        pass

    # Step 5: The postintro method will be called right after the intro is printed. So we do a login from here
    async def postintro(self):
        while True:
            status = await self.login()
            if status:
                print("Logged in", file=self.stdout)
                return

    # Called when the CLI is about to exit. Can be used to feed the information
    # in sub-cli contexts to parent CLI
    async def on_exit(self):
        pass

    async def login(self):
        username = await self.input("Username: ", from_stdin=True)
        if not await self.validate_username(username):
            print("Invalid username.", file=self.stdout)
            return False
        password = await self.input("Password: ", show_char=False, from_stdin=True)
        if not await self.validate_password(username, password):
            print("Invalid password.", file=self.stdout)
            return False

        # Step 8: If login is successful, open a new CLI context, which will be handling exec commands
        #         The CLI class is ExecCmd, It does not inherit the parent cli grammar
        #         Also match_parent_grammar is False, so if the input cannot be matched in the CLI,
        #         it will not attempt to exit if the input matches with the parent rules
        await self.enter_context(
            ExecCmd,
            use_parent_grammar=False,
            prompt="nessaid-router-box # ",
            match_parent_grammar=False, disable_default_hooks=True
        )
        return True


if __name__ == '__main__':
    # Step 1: Introduction message for the initialCLI
    intro = "\n" * 3 + "Welcome to nessaid-cli router-box" + "\n" * 2 + "Plese login" + "\n" * 2
    # Step 2: Create the inital CLI object. Which is used to authenticate.
    # Step 3: prompt is self explanatory. disable_default_hooks will disable the commands available  by default
    #       in the base clas, ie. NessaidCmd
    LoginPrompt(prompt="nessaid-router-box (Not logged in) # ", disable_default_hooks=True).run(intro=intro)
