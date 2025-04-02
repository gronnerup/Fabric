#---------------------------------------------------------
# Default values
#---------------------------------------------------------
action = "Create" # Options: Create/Delete. Defaults to Create if not set
default_environments = "dev,tst,prd"

#---------------------------------------------------------
# Main script
#---------------------------------------------------------
import os, sys, argparse, re
from datetime import datetime

start_time = datetime.now()

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
sys.path.append(os.getcwd())

import modules.fabric_functions as fabfunc
import modules.misc_functions as miscfunc
import modules.auth_functions as authfunc
import modules.azure_functions as azfunc
import modules.devops_functions as devopsfunc

# Get arguments
parser = argparse.ArgumentParser(description="Fabric solution setup arguments")
parser.add_argument("--environments", required=False, default=default_environments, help="Comma seperated list of tiers to setup. Default is dev.")
parser.add_argument("--fabric_token", required=False, default=None, help="Microsoft Entra ID token for Fabric API based on signed in user. Default is None.")
parser.add_argument("--management_token", required=False, default=None, help="Microsoft Entra ID token for Azure Management based on signed in user. Default is None.")
parser.add_argument("--action", required=False, default=action, help="Indicates the action to perform (Create/Delete). Default is Create.")

args = parser.parse_args()
environments = args.environments.split(",")
fabric_token = args.fabric_token
action = args.action.lower()

fabric_upn_token = None
# if fabric_token:
#     fabric_upn_token = fabric_token if not authfunc.is_service_principal(fabric_token) else None

env_cnt = len(environments)
for environment in environments:
    env_cnt -= 1 if (authfunc.get_environment_credentials(environment, os.path.join(os.path.dirname(__file__), f'../../credentials/'))) is not None else 0

env_credentials_exist = True if env_cnt == 0 else False

if env_credentials_exist == False and not fabric_token:
    miscfunc.print_info("Authenticating using User Identity as no token has been provided and credential file is not present...", bold = True)
    credential = authfunc.create_credentials_from_user()
    fabric_upn_token = credential.get_token("https://api.fabric.microsoft.com/.default").token
    fabric_token = fabric_upn_token

response = "n"
while True and not fabric_token:
    response = input("\n\033[1;94mUse User Identity for non-Service Principal supported APIs (Y/N)?\033[0m\n").strip().lower()
    if response in ["y", "n"]:
        break
    print("Invalid input. Please enter Y or N.")

if response == "y":
    credential = authfunc.create_credentials_from_user()
    fabric_upn_token = credential.get_token("https://api.fabric.microsoft.com/.default").token

yaml_file = os.path.join(os.path.dirname(__file__), f'../../cicd/parameters/parameter.yml') # Set to None when skipping creation of yml paramater file. Also see https://microsoft.github.io/fabric-cicd/
all_environments = {}

if action == "create":
    # Create Fabric solution in the specified environments

    for environment in environments:
        # Load JSON files and merge
        main_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/infrastructure.json'))
        env_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/infrastructure.{environment}.json'))
        env_definition = miscfunc.merge_json(main_json, env_json)

        if env_definition:
            env_credentials = authfunc.get_environment_credentials(environment, os.path.join(os.path.dirname(__file__), f'../../credentials/'))

            if env_credentials:
                fabric_token = authfunc.get_access_token(env_credentials["tenant_id"], env_credentials["app_id"], env_credentials["app_secret"], 'https://api.fabric.microsoft.com')
            
            miscfunc.print_header(f"Setting up {environment} environment")
            
            solution_name = env_definition.get("name")
            layers = env_definition.get("layers")
            default_capacityid = env_definition.get("generic").get("capacity_id")
            
            for layer, layer_definition in layers.items():
                print("")
                workspace_name = solution_name.format(layer=layer, environment=environment)
                workspace = fabfunc.create_workspace(fabric_token, workspace_name, "Workspace automatically created from setup script.")
                workspace_id = workspace.get("id")
                
                # Update layer_definition
                layer_definition["workspace_id"] = workspace_id
                layer_definition["workspace_name"] = workspace_name

                capacity_id = layer_definition.get("capacity_id", default_capacityid)
                fabfunc.assign_workspace_to_capacity(fabric_token, workspace_id, capacity_id)
                
                print(f"  → Assigning workspace permissions... ", end="")
                permissions = layer_definition.get("permissions") or env_definition.get("generic", {}).get("permissions")
                miscfunc.print_success("Done!")
                
                if permissions:
                    for permission, definitions in permissions.items():
                        for definition in definitions:
                            fabfunc.add_workspace_user(fabric_token, workspace_id, permission, definition.get("type"), definition.get("id"))

                if layer_definition.get("items"):
                    print(f"  → Creating workspace items...")
                    for item_type, items in layer_definition.get("items").items():
                        for item in items:
                            item_result = fabfunc.create_item(fabric_token, workspace_id, item.get("item_name"), item_type, None, True, True)
                            
                            if not item_result:
                                continue # Proceed to next item if item_creation failed.

                            item["id"] = item_result.get("id")

                            if item_type == "Lakehouse":
                                item_result = fabfunc.get_lakehouse_sqlendpoint(fabric_token, workspace_id, item_result.get("id"))
                                item["sql_endpoint_id"] = item_result.get("properties", {}).get("sqlEndpointProperties", {}).get("id", {})
                                item["sql_endpoint_connectionstring"] = item_result.get("properties", {}).get("sqlEndpointProperties", {}).get("connectionString", {})
                            elif item_type == "SQLDatabase":
                                item_result = fabfunc.get_sqldatabase(fabric_token, workspace_id, item_result.get("id"))
                                item["sql_database_fqdn"] = item_result.get("properties", {}).get("serverFqdn", {})
                                item["sql_database_name"] = item_result.get("properties", {}).get("databaseName", {})
                                item["sql_database_connectionstring"] = f"Server={item_result.get("properties", {}).get("serverFqdn", {})};Authentication=Active Directory Service Principal;Encrypt=True;Database={item_result.get("properties", {}).get("databaseName", {})};User Id={env_credentials["app_id"]};Password={env_credentials["app_secret"]}"

                                if item.get("sql_script"):
                                    script_file = os.path.join(os.path.dirname(__file__), item.get("sql_script"))
                                    if os.path.exists(script_file):
                                        with open(script_file, 'r') as file:
                                            sql_script = file.read()
                                            conn = fabfunc.get_fabric_database_connection(fabric_token, item["sql_database_fqdn"], item["sql_database_name"])
                                            if conn:
                                                fabfunc.sql_execute_nonquery(conn, sql_script)
                                                conn.close
        
                            if env_credentials is not None and item.get("connection_name") and item_type in {"Lakehouse", "SQLDatabase"} and (item.get("sql_database_fqdn") or item.get("sql_endpoint_connectionstring")):
                                connection = item.get("connection_name").format(layer=layer, environment=environment)
                                
                                datasource = fabfunc.create_sql_datasource(
                                    fabric_token, 
                                    connection, 
                                    item["sql_database_fqdn"] if item_type == "SQLDatabase" else item["sql_endpoint_connectionstring"], 
                                    item["sql_database_name"] if item_type == "SQLDatabase" else item.get("item_name"),
                                    env_credentials["tenant_id"], 
                                    env_credentials["app_id"], 
                                    env_credentials["app_secret"])
                        
                                if permissions and datasource:
                                    print(f"      - Assigning datasource permissions... ", end="")
                                    for permission, definitions in permissions.items():
                                        for definition in definitions:
                                            role = "Owner" if permission == "Admin" else "User"
                                            fabfunc.add_datasource_user(fabric_token, datasource.get("clusterId"), datasource.get("id"), 
                                                role, definition.get("type"), definition.get("id"), False)
                                    miscfunc.print_success("Done!")
                                
                                    item["pbi_connection_name"] = connection
                                    item["pbi_connection_id"] = datasource.get("id")
                                    item["pbi_connection_clusterid"] = datasource.get("clusterId")
                    
                if layer_definition.get("private_endpoints"):
                    print("  → Creating private endpoints... ")
                    for private_endpoint in layer_definition.get("private_endpoints"):
                        mpe = fabfunc.create_workspace_managed_private_endpoint(fabric_token, workspace_id, private_endpoint.get("name"), private_endpoint.get("id"))
                        if(private_endpoint.get("auto_approve")) and mpe:
                            print("      - Approving private endpoint connection... ", end="")
                            if mpe.get("connectionState", {}).get("status") != "Approved":
                                if management_token is None and env_credentials is not None:
                                    management_token = authfunc.get_access_token(env_credentials["tenant_id"], env_credentials["app_id"], env_credentials["app_secret"], 'https://management.core.windows.net')
                                elif credential is not None:
                                    management_token = credential.get_token("https://management.core.windows.net/.default").token

                                connection_name = f"{workspace_id}.{private_endpoint.get("name")}-conn"
                                azfunc.approve_private_endpoint(management_token, private_endpoint.get("id"), connection_name)
                            else:
                                miscfunc.print_warning("Skipped! Private endpoint connection is already approved.")    

                git_default_props = env_definition.get("generic").get("git_integration")
                git_layer_props = layer_definition.get("git_integration")

                if git_default_props and git_layer_props and fabric_upn_token:
                    print (f"  → Setting up Git integration for workspace {workspace_name}")

                    connect_response = fabfunc.connect_workspace_to_git(
                        fabric_upn_token, 
                        workspace_id, 
                        git_layer_props.get("devops_organization", git_default_props.get("devops_organization")),
                        git_layer_props.get("devops_project", git_default_props.get("devops_project")), 
                        git_layer_props.get("devops_repo", git_default_props.get("devops_repo")), 
                        git_layer_props.get("devops_branch", git_default_props.get("devops_branch")), 
                        git_layer_props.get("devops_folder", git_default_props.get("devops_folder")))
                    
                    if connect_response is not None:
                        init_response = fabfunc.initialize_workspace_git_connection(fabric_upn_token, workspace.get('id'))
                        if init_response and init_response.get("requiredAction") != "None" and init_response.get("remoteCommitHash"):
                            fabfunc.update_workspace_from_git(fabric_upn_token, workspace.get('id'), init_response["remoteCommitHash"])

                wsicon_default = env_definition.get("generic").get("workspace_icon")
                wsicon_layer = layer_definition.get("workspace_icon")

                if (wsicon_default or wsicon_layer) and fabric_upn_token:
                    capacities = fabfunc.get_capacities(fabric_token)
                    match = re.match(r"(https://[^/]+/)", capacities.get("@odata.context"))
                    cluster_base_url = match.group(1) if match else None
                    icon_path = os.path.join(os.path.dirname(__file__), wsicon_layer if wsicon_layer else wsicon_default)
                    if os.path.exists(icon_path):
                        base64_str = miscfunc.image_to_base64(icon_path)
                        fabfunc.set_workspace_icon(fabric_upn_token, workspace.get('id'), cluster_base_url, base64_str)

        else:
            miscfunc.print_warning(f"No environment definition found for {environment}... Skipping setup!")

        print("")
    
        all_environments[environment] = env_definition

    # Create parameter file
    devops_access_token = os.getenv("SYSTEM_ACCESSTOKEN")
    if yaml_file:
        miscfunc.print_info(f"→ Generating Parameter YML file... ", bold=True, end="")
        yml_data = miscfunc.create_parameter_yml(all_environments)
        if devops_access_token:
            org_url = os.getenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
            project_name = os.getenv("SYSTEM_TEAMPROJECT")
            repo_name = os.getenv("BUILD_REPOSITORY_NAME")
            org_name = org_url.split('/')[3]
            branch_data = devopsfunc.get_branch(devops_access_token, org_name, project_name, repo_name, "main")

            if not branch_data is None and branch_data.get("count",0) > 0 :
                object_id = branch_data['value'][0]['objectId']
                yml_string = miscfunc.generate_yaml_string(yml_data)

                try:
                    push_result = devopsfunc.push_to_repo( # Push to main branch
                        devops_access_token, org_name, project_name, repo_name, "main", object_id,
                        "/automation/cicd/parameters/parameter.yml", yml_string, "Update parameter file based on latest solution setup."
                    )
                    miscfunc.print_success(f"Done!") if push_result is not None else miscfunc.print_success(f"Failed!")
                except:
                    miscfunc.print_success(f"Failed!")  
        else:
            try:
                miscfunc.save_yaml(yaml_file, yml_data)
                miscfunc.print_success(f"Done!")
            except:
                miscfunc.print_success(f"Failed!")

else:  
    # Delete Fabric solution in the specified environments
    for environment in environments:
        env_credentials = authfunc.get_environment_credentials(environment, os.path.join(os.path.dirname(__file__), f'../../credentials/'))

        if fabric_token is None and env_credentials is not None:
            fabric_token = authfunc.get_access_token(env_credentials["tenant_id"], env_credentials["app_id"], env_credentials["app_secret"], 'https://api.fabric.microsoft.com')
        elif fabric_token is None:
            credential = authfunc.create_credentials_from_user()
            fabric_token = credential.get_token("https://api.fabric.microsoft.com/.default").token

        # Load JSON files and merge
        main_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/infrastructure.json'))
        env_json = miscfunc.load_json(os.path.join(os.path.dirname(__file__), f'../environments/infrastructure.{environment}.json'))
        env_definition = miscfunc.merge_json(main_json, env_json)
    
        miscfunc.print_header(f"Deleting {environment} environment")
        
        solution_name = env_definition.get("name")
        layers = env_definition.get("layers")
        default_capacityid = env_definition.get("generic").get("capacity_id")

        for layer, layer_definition in layers.items():
            workspace_name = solution_name.format(layer=layer, environment=environment)
            workspace = fabfunc.get_workspace_by_name(fabric_token, workspace_name)
            if workspace:
                fabfunc.delete_workspace(fabric_token, workspace.get("id"), workspace_name)
            else:
                miscfunc.print_warning(f"Did not find any workspace named {workspace_name}... Skipping deletion!")
            
            if layer_definition.get("items"):
                for item_type, items in layer_definition.get("items").items():
                    for item in items:    
                        if item.get("connection_name") and item_type in {"Lakehouse", "SQLDatabase"}:
                            connection = item.get("connection_name").format(layer=layer, environment=environment)  
                            datasource = fabfunc.get_sql_datasource(fabric_token, connection)
                            if datasource:
                                fabfunc.delete_datasource(fabric_token, datasource.get("clusterId"), datasource.get("id"))

duration = datetime.now() - start_time
print(f"\nScript duration: {duration}\n")