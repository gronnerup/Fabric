import fabric_functions as fabfunc
from datetime import datetime

start_time = datetime.now()

#region Service principal settings and fetching of access_tokens etc.

# Load the credentials from the credentials.json file. Remove this and use hardcoded values if credentials file is not used. 
credentials = fabfunc.get_credentials_from_file("credentials.json")

### Service principal settings
tenant_id = credentials["tenant_id"]
app_id = credentials["app_id"]
app_secret = credentials["app_secret"]

### Get Fabric access token for use with Fabric REST APIs
fabric_access_token = fabfunc.get_access_token(tenant_id, app_id, app_secret, 'https://api.fabric.microsoft.com')

#endregion

#region Fabric solution setup
fabric_solution_name = 'MyDataPlatform - {stage} [{environment}]'
fabric_environments = ['dev', 'tst', 'prd']
fabric_stages = ['Data', 'Ingest', 'Prepare', 'Serve']
#endregion

#region Clean up solution
for environment in fabric_environments:
    print(f"############################## Clean up {environment} environment ##############################")
    for stage in fabric_stages:
        workspace_name = fabric_solution_name.format(stage=stage, environment=environment)
        workspace = fabfunc.get_workspace_by_name(fabric_access_token, workspace_name)
        if not workspace is None:
            fabfunc.delete_workspace(fabric_access_token, workspace.get('id'))
    print("")

duration = datetime.now() - start_time
print(f"Script duration: {duration}")
#endregion
