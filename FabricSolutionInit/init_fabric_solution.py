import fabric_functions as fabfunc
from azure.identity import InteractiveBrowserCredential
from datetime import datetime

start_time = datetime.now()

#region Service principal settings and fetching of access_tokens etc.
# Load the credentials from the credentials.json file. Remove this and use hardcoded values if credentials file is not used. 
credentials = fabfunc.get_credentials_from_file("credentials.json")

tenant_id = credentials["tenant_id"]
app_id = credentials["app_id"]
app_secret = credentials["app_secret"]

fabric_access_token = fabfunc.get_access_token(tenant_id, app_id, app_secret, 'https://api.fabric.microsoft.com')
#endregion

#region Fabric solution setup
fabric_solution_name = 'MyDataPlatform - {stage} [{environment}]'

#region Fabric environments
fabric_environments = {
        "dev": {
            "capacity_id": "00000000-0000-0000-0000-000000000000",
            "permissions": {
                "Admin": [
                    {"type": "Group", "id": "00000000-0000-0000-0000-000000000000"},
                    {"type": "User", "id": "user1@email.com"},
                ]
            }
        },
        "tst": {
            "capacity_id": "00000000-0000-0000-0000-000000000000",
            "permissions": {
                "Admin": [
                    {"type": "Group", "id": "00000000-0000-0000-0000-000000000000"}
                ]
            }
        },
        "prd": {
            "capacity_id": "00000000-0000-0000-0000-000000000000",
            "permissions": {
                "Admin": [
                    {"type": "Group", "id": "00000000-0000-0000-0000-000000000000"}
                ]
            }
        }
    }
#endregion

#region Fabric Workspaces stages
fabric_stages = {
        "Data": { "lakehouses": ["Bronze", "Silver", "Gold"], "schema": True },
        "Ingest": { },
        "Prepare": { 
            "private_endpoints" : 
            [
                    {
                        "name": "mpe-kv-peerinsights-dev", 
                        "auto_approve": True,
                        "id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-peerinsights-dev/providers/Microsoft.KeyVault/vaults/kv-peerinsights-dev"
                    },
            ] 
        },
        "Serve": { }
    }

# Example of seperating lakehouse into multiple workspaces
# fabric_stages = {
#         "Data - Bronze": { "lakehouses": ["Bronze"] },
#         "Data - Silver": { "lakehouses": ["Silver"] },
#         "Data - Gold": { "lakehouses": ["Gold"] },
#         "Ingest": { },
#         "Prepare": { },
#         "Serve": { }
#     }
#endregion

#region Fabric Solution Git setup
fabric_git_setup = {
        "dev": { 
            "Prepare": { 
                "DevOpsOrgName" : "YourDevOpsOrgName",
                "DevOpsProjectName" : "Fabric Data Platform",
                "DevOpsRepoName" : "Fabric Data Platform",
                "DevOpsDefaultBranch" : "main",
                "DevOpsFabricSolutionFolder" : "/solution/fabric/Prepare"
                },
            "Ingest": { 
                "DevOpsOrgName" : "PeerInsights",
                "DevOpsProjectName" : "Fabric Data Platform",
                "DevOpsRepoName" : "Fabric Data Platform",
                "DevOpsDefaultBranch" : "main",
                "DevOpsFabricSolutionFolder" : "/solution/fabric/Ingest"
                },
            "Serve": { 
                "DevOpsOrgName" : "PeerInsights",
                "DevOpsProjectName" : "Fabric Data Platform",
                "DevOpsRepoName" : "Fabric Data Platform",
                "DevOpsDefaultBranch" : "main",
                "DevOpsFabricSolutionFolder" : "/solution/fabric/Serve"
                }   
        }
    }
#endregion
#endregion

#region Setup Fabric solution
for environment, env_props in fabric_environments.items():
    
    print(f"############################## Setting up {environment} environment ##############################")
    
    for stage, stage_props in fabric_stages.items():
        workspace_name = fabric_solution_name.format(stage=stage, environment=environment)
        workspace = fabfunc.create_workspace(fabric_access_token, workspace_name, "Workspace automatically created from init_fabric.py script.")
        workspace_id = workspace.get('id')

        fabfunc.assign_workspace_to_capacity(fabric_access_token, workspace_id, env_props.get("capacity_id"))

        if not env_props.get("permissions") is None:
            for permission, permission_definitions in env_props.get("permissions").items():
                for definition in permission_definitions:
                    fabfunc.add_workspace_user(fabric_access_token, workspace_id, permission, definition.get("type"), definition.get("id") )

        if not stage_props.get("lakehouses") is None:
            for lakehouse in stage_props.get("lakehouses"):
                fabfunc.create_fabric_item(fabric_access_token, workspace_id, lakehouse, "Lakehouse", None, stage_props.get("schema"))

        if not stage_props.get("private_endpoints") is None:
            for private_endpoint in stage_props.get("private_endpoints"):
                fabfunc.create_workspace_managed_private_endpoint(fabric_access_token, workspace_id, private_endpoint.get("name"), private_endpoint.get("id"))
                if(private_endpoint.get("auto_approve")):
                    connection_name = f"{workspace_id}.{private_endpoint.get("name")}-conn"
                    management_access_token = fabfunc.get_access_token(tenant_id, app_id, app_secret, 'https://management.core.windows.net')
                    fabfunc.approve_private_endpoint(management_access_token, private_endpoint.get("id"), connection_name)    
            
    print ("")


if not fabric_git_setup is None:
    print(f"############################## Setting up git integrations ##############################")
    credential : InteractiveBrowserCredential = fabfunc.create_credentials_from_user()
    fabric_access_token_user = fabfunc.get_access_token_from_credentials(credential, 'https://api.fabric.microsoft.com/.default')

    for environment, stages in fabric_git_setup.items():
        for stage, git_props in stages.items():
            workspace_name = fabric_solution_name.format(stage=stage, environment=environment)
            workspace = fabfunc.get_workspace_by_name(fabric_access_token, workspace_name)
            print (f"Setting up Git integration for workspace {workspace_name}")

            connect_response = fabfunc.connect_workspace_to_git(
                fabric_access_token_user, 
                workspace.get('id'), 
                git_props.get("DevOpsOrgName"),
                git_props.get("DevOpsProjectName"), 
                git_props.get("DevOpsRepoName"), 
                git_props.get("DevOpsDefaultBranch"), 
                git_props.get("DevOpsFabricSolutionFolder"))
            
            if not connect_response is None:
                init_response = fabfunc.initialize_workspace_git_connection(fabric_access_token_user, workspace.get('id'))
                if init_response and init_response.get("requiredAction") != "None" and init_response.get("remoteCommitHash"):
                    fabfunc.update_workspace_from_git(fabric_access_token_user, workspace.get('id'), init_response["remoteCommitHash"])
    
            print("")

duration = datetime.now() - start_time
print(f"Script duration: {duration}")
#endregion
