#---------------------------------------------------------
# Default values
#---------------------------------------------------------
default_solution_path = "C:\\repos\\PeerInsights\\FabCon25\\solution"
default_item_types_in_scope = "Notebook,DataPipeline"
default_layers_in_scope = "prepare,ingest"
default_environment = "dev"

#---------------------------------------------------------
# Main script
#---------------------------------------------------------
import os, sys, argparse, re
from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, change_log_level
from datetime import datetime

start_time = datetime.now()

dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..')
os.chdir(dir)
sys.path.append(os.getcwd())

import modules.fabric_functions as fabfunc
import modules.misc_functions as miscfunc
import modules.auth_functions as authfunc

# Get arguments 
parser = argparse.ArgumentParser(description="Fabric release arguments")
parser.add_argument("--fabric_token", required=False, default=None, help="Microsoft Entra ID token for Fabric API based on SPN or UPN.")
parser.add_argument("--env", required=False, default=default_environment, help="Name of environment to release.")
parser.add_argument("--layers", required=False, default=default_layers_in_scope, help="Comma seperated list of layers to deploy. Can also be single layer.")
parser.add_argument("--item_types", required=False, default=default_item_types_in_scope, help="Comma seperated list of item types in scope. Must match Fabric ItemTypes exactly.")
parser.add_argument("--solution_path", required=False, default=default_solution_path, help="Path the the solution repository where items are stored.")

args = parser.parse_args()
fabric_token = args.fabric_token
environment = args.env
included_layers_list = [layer.strip().lower() for layer in args.layers.split(",")]
item_type_list = args.item_types.split(",")
solution_path = args.solution_path

is_devops_run = True if os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI") else False

# Load JSON files and merge
main_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/infrastructure.json'))
env_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/infrastructure.{environment}.json'))
env_definition = miscfunc.merge_json(main_json, env_json)

env_credentials = authfunc.get_environment_credentials(environment, os.path.join(os.path.dirname(__file__), f'../../credentials/'))

if not fabric_token and env_credentials:
    fabric_token = authfunc.get_access_token(env_credentials["tenant_id"], env_credentials["app_id"], env_credentials["app_secret"], 'https://api.fabric.microsoft.com')
elif not fabric_token and not env_credentials:
    miscfunc.print_info("Authenticating using User Identity as no token has been provided and credential file is not present...", bold = True)
    credential = authfunc.create_credentials_from_user()
    fabric_token = credential.get_token("https://api.fabric.microsoft.com/.default").token

miscfunc.print_header(f"Build Fabric items for release")

token_credential = authfunc.StaticTokenCredential(fabric_token)

if env_definition:
    solution_name = env_definition.get("name")
    layers = env_definition.get("layers")

    layer_deploy_order = ["Store", "Prepare", "Ingest", "Model", "Orchestrate"]
    sorted_layers = {key: layers[key] for key in layer_deploy_order if key in layers}

    #Build mappings for handing cross-workspace references i.e. Data Pipelines referencing notebooks
    item_mapping = {}
    for layer, layer_definition in sorted_layers.items():
        if layer.lower() in included_layers_list:        
            workspace_name = solution_name.format(layer=layer, environment=environment)
            workspace_id = fabfunc.get_workspace_by_name(fabric_token, workspace_name).get("id")

            repo_dir = os.path.join(solution_path, layer.lower())
            
            target_workspace = FabricWorkspace(
                workspace_id=workspace_id,
                environment=environment,
                repository_directory=repo_dir,
                item_type_in_scope=item_type_list,
                token_credential=token_credential,
            )

            # Dictionary to store {item_guid: logical_id}
            for item_name in target_workspace.repository_items.values():
                for item_details in item_name.values():
                    item_mapping[item_details.guid] = item_details.logical_id  # Map GUID to logical ID

    for layer, layer_definition in sorted_layers.items():
        if layer.lower() in included_layers_list:        
            workspace_name = solution_name.format(layer=layer, environment=environment)
            workspace_id = fabfunc.get_workspace_by_name(fabric_token, workspace_name).get("id")

            miscfunc.print_info(f"Building {layer}!", True)

            repo_dir = os.path.join(solution_path, layer.lower())

            target_workspace = FabricWorkspace(
                workspace_id=workspace_id,
                environment=environment,
                repository_directory=repo_dir,
                item_type_in_scope=item_type_list,
                token_credential=token_credential,
            )

            for item_name in target_workspace.repository_items.values():
                for item_details in item_name.values():
                    item_mapping[item_details.guid] = item_details.logical_id  # Map GUID to logical ID

            pattern = re.compile("|".join(map(re.escape, item_mapping.keys())))

            for item in target_workspace.repository_items.values():
                for item_details in item.values():
                    for file in item_details.item_files:
                        content = pattern.sub(lambda match: item_mapping[match.group()], file.contents)
                        if(item_details.name =='Controller - Full'):
                            with open(file.file_path, "w", encoding="utf-8") as item_file:
                                item_file.write(content)                  

else:
    miscfunc.print_error(f"No environment definition found for environment {environment}! Build has been skipped.", True)