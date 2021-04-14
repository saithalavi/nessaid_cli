# Copyright 2021 by Saithalavi M, saithalavi@gmail.com
# All rights reserved.
# This file is part of the Nessaid CLI Framework, nessaid_cli python package
# and is released under the "MIT License Agreement". Please see the LICENSE
# file included as part of this package.
#

token TEST_NUMBER RangedIntToken(1, 100); // Token to match integer between 1 and 100
token STRING_TOKEN RangedStringToken(5, 10); // Token to match a string of length 5 to 10

command1[$number_var]:
	"command\n1"
	TEST_NUMBER
	<<
		print("Incoming number is:", $number_var); # This uses inline print function
		call print("Input number is:", $2); /* Note call prefix. So routed to the CLI class's print function */
	>>
	;

command2[$str_var]:
	"command2"
	STRING_TOKEN
	<<
		print("Incoming str is:", $str_var);
		call print("Input str is:", $2);
	>>
	;

command3:
	"command3"
	<< print("This is simply command3"); >>
	;

exit:
	("exit" | "quit")
	<<call exit();>>
	;

test_grammar:
	<<
		$number = 5;
		$msg = "This is test_grammar";
	>>
	command1[$number]
	|
	command2[$msg]
	|
	command3
	|
	exit
	;