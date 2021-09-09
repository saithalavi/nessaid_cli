from nessaid_cli.cmd import NessaidCmd


class BecnhmarkCmd(NessaidCmd):

    async def do_orderless(self):
        r"""
        (
        "orderless"
        (("1", {"2"}, "3"), ("a", {"b"}, "c")) * 2
        {("1", {"2"}, "3"), ("a", {"b"}, "c")} * 4
        ) * (1: 50)
        """
        print("OK")


intro = """
Copy and paste the benchmark expression from benchmark.txt
make sure timing and profiling are enabled before.

use

# cmd-t on

and

# cmd-p on

"""

BecnhmarkCmd(prompt="# ").run()
