#---------------------------------------------------------
# Feature settings
#---------------------------------------------------------
branch_name = "feature/pg/issue1" 
feature_prefix = "feature/"

#---------------------------------------------------------
# Main script
#---------------------------------------------------------
import os, sys
from datetime import datetime

start_time = datetime.now()

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
sys.path.append(os.getcwd())

import modules.fabric_functions as fabfunc
import modules.misc_functions as miscfunc
import modules.auth_functions as authfunc

feature_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/feature.json'))
layers = feature_json.get("layers")
dev_env_name = feature_json.get("feature_name")
git_integration = feature_json.get("git_integration")

credential = authfunc.create_credentials_from_user()
fabric_token = credential.get_token("https://api.fabric.microsoft.com/.default").token

if git_integration:
    org_name = feature_json.get("git_integration").get("devops_organization")
    project_name = feature_json.get("git_integration").get("devops_project")
    repo_name = feature_json.get("git_integration").get("devops_repo")
    base_branch = feature_json.get("git_integration").get("devops_base_branch")
        
miscfunc.print_header(f"Connecting feature branch to feature workspaces")
ws_branch_name = branch_name.replace(f"{feature_prefix}", "")

for layer, layer_definition in layers.items():
    feature_name = feature_json.get("feature_name")
    workspace_name = dev_env_name.format(feature_name=ws_branch_name, layer_name=layer)

    workspace = fabfunc.get_workspace_by_name(fabric_token, workspace_name)
    workspace_id = workspace.get("id")

    if git_integration:
        print (f"  → Setting up Git integration for workspace {workspace_name} connection to feature {branch_name}.")

        connect_response = fabfunc.connect_workspace_to_git(
            fabric_token, 
            workspace_id, 
            org_name, 
            project_name,
            repo_name,
            branch_name,
            layer_definition.get("git_folder"))

        if connect_response:
            init_response = fabfunc.initialize_workspace_git_connection(fabric_token, workspace_id)
            if init_response and init_response.get("requiredAction") != "None" and init_response.get("remoteCommitHash"):
                fabfunc.update_workspace_from_git(fabric_token, workspace_id, init_response["remoteCommitHash"])
    
    print ("")

duration = datetime.now() - start_time
print(f"\nScript duration: {duration}\n")