#---------------------------------------------------------
# Default values
#---------------------------------------------------------
scope = "https://api.fabric.microsoft.com/.default"
copy_to_clipboard = True

#---------------------------------------------------------
# Main script
#---------------------------------------------------------
import os, sys, pyperclip
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
sys.path.append(os.getcwd())

import modules.misc_functions as miscfunc
import modules.auth_functions as authfunc

credential = authfunc.create_credentials_from_user()
fabric_upn_token = credential.get_token(scope).token

miscfunc.print_header("Generating Fabric UPN token")
if copy_to_clipboard:
    pyperclip.copy(fabric_upn_token)
    miscfunc.print_info("Token copied to clipboard!", True)
else:  
    print(fabric_upn_token)