import requests
import base64
import pyodbc
import time 
import json, struct
import modules.misc_functions as mf

fabric_baseurl = "https://api.fabric.microsoft.com/v1"
powerbi_baseurl = "https://api.powerbi.com/v1.0/myorg"
powerbi_baseurl_v2 = "https://api.powerbi.com/v2.0/myorg"

def get_workspace_by_name(access_token, workspace_name):
    """
    Retrieves a workspace by its name from Microsoft Power BI.

    Args:
        headers (dict): A dictionary containing the authorization header, including an OAuth 2.0 bearer token.
        workspace_name (str): The name of the workspace to retrieve.

    Returns:
        dict or None: A dictionary containing the details of the first workspace found with the specified name. 
                      Returns None if no workspace with the given name is found or if an error occurs.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{powerbi_baseurl}/groups?$filter=name eq '{workspace_name}'", headers=headers)
        response.raise_for_status()
        workspaces = response.json().get("value", [])
        if workspaces:
            return workspaces[0]
        return None
    except requests.exceptions.RequestException as e:
        return None
    

def get_workspace_by_id(access_token, workspace_id):
    """
    Retrieves a workspace by its id from Microsoft Power BI.

    Args:
        access_token (str): The OAuth access token used to authorize the API request.
        workspace_id (str): The id of the workspace to retrieve.

    Returns:
        dict or None: A dictionary containing the details of the first workspace found with the specified id. 
                      Returns None if no workspace with the given id is found or if an error occurs.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{powerbi_baseurl}/groups/{workspace_id}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None
    

def create_workspace(access_token, workspace_name, workspace_description, print_output:bool = True):
    """
    Creates a new workspace in Microsoft Fabric if a workspace with the specified name does not already exist.

    Args:
        access_token (str): OAuth 2.0 bearer token for authenticating the API request.
        workspace_name (str): The name of the workspace to create.
        workspace_description (str): A description for the new workspace.

    Returns:
        dict or None: A dictionary containing the workspace details if the workspace is successfully created. 
                      Returns None if the workspace already exists or if an error occurs during creation.
    """
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    mf.print_info(value=f"→ Setting up workspace {workspace_name}... ", bold=True, end="") if print_output == True else None  
    
    workspace = get_workspace_by_name(access_token, workspace_name)

    if workspace is None:
        body = {
            "displayName": workspace_name,
            "description": workspace_description
        }
        try:
            response = requests.post(f"{fabric_baseurl}/workspaces", headers=headers, json=body)
            response.raise_for_status()
            mf.print_success(f"Done! Workspace id: {response.json()['id']}", bold=True) if print_output == True else None
            return response.json()
        except requests.exceptions.RequestException as e:
            mf.print_error(f"Failed! Error creating workspace: {e}", bold=True) if print_output == True else None
            return None
    else:
        if print_output: 
            mf.print_warning(f"Skipped! Workspace already exists ({workspace.get("id")}).", bold=True) if print_output == True else None
        return workspace
    

def assign_workspace_to_capacity(access_token, workspace_id, capacity_id, print_output:bool = True):
    """
    Assigns a specified workspace to a given capacity in Power BI.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the workspace to assign to the capacity.
        capacity_id (str): The unique identifier of the capacity to which the workspace will be assigned.

    Returns:
        Boolean: Returns True if success and False if failed!
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "capacityId": capacity_id
    }

    print(f"  → Assigning workspace to capacity {capacity_id}... ", end="") if print_output == True else None
    
    workspace = get_workspace_by_id(access_token, workspace_id)
    
    if workspace.get("capacityId") == capacity_id:
        mf.print_warning(f"Skipped! Specified capacity already assigned.") if print_output == True else None
        return True

    try:
        response = requests.post(f"{powerbi_baseurl}/groups/{workspace_id}/AssignToCapacity", headers=headers, json=body)
        response.raise_for_status()
        if workspace.get("capacityId") is not None:
            mf.print_success(f"Updated! A different capacity was already assigned {workspace.get("capacityId")}. Changed to: {capacity_id} ") if print_output == True else None
        else:
            mf.print_success(f"Done!") if print_output == True else None
        
        return True
    except requests.exceptions.RequestException as e:
        mf.print_error(f"Failed! Could not assign workspace to capacity.") if print_output == True else None
        return False



def delete_workspace(access_token, workspace_id, workspace_name = "", print_output:bool = True):
    """
    Removes a specified workspace from Microsoft Power BI.

    Args:
        access_token (str): OAuth 2.0 bearer token used to authenticate the API request.
        workspace_id (str): The unique identifier of the workspace to be removed.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{powerbi_baseurl}/groups/{workspace_id}"
    
    print(f"  → Deleting workspace {workspace_name}... ", end="") if print_output == True else None
    
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status() 
        mf.print_success(f"Done.") if print_output == True else None
    except requests.exceptions.RequestException as e:
        error_details = response.json().get("error", {}).get("message", str(e))
        if print_output:
            mf.print_error(f"Failed! Could not delete workspace {workspace_name} ({workspace_id})") if print_output == True else None


def add_workspace_user(access_token, workspace_id, access_role, identity_type, identity_identifier):
    """
    Assigns a specified access role to a user or group within a Power BI workspace.

    Args:
        access_token (str): The OAuth access token used to authorize the API request.
        workspace_id (str): The unique identifier of the Power BI workspace to which the role assignment applies.
        access_role (str): The role to assign to the user or group. Acceptable values are "Admin", "Contributor", "Member", "Viewer", or "None".
        identity_type (str): The type of identity being assigned. Acceptable values are "User" (for email-based identification) 
            and "Group" or "App" for Entra ID groups or service principals.
        identity_identifier (str): The identifier for the identity. For "User", this should be an email address; 
            for other types, this should be a unique identifier.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "identifier": identity_identifier,
        "groupUserAccessRight": access_role,
        "principalType": identity_type
    }
 
    print(f"    • Updating workspace role assignment for {identity_type} {identity_identifier}... ", end="")

    try:
        response = requests.post(f"{powerbi_baseurl}/groups/{workspace_id}/users", headers=headers, json=body)
        response.raise_for_status()
        mf.print_success(f"Done!")
    except requests.exceptions.RequestException as e:
        if response is not None:
            error_code = response.json().get("error", {}).get("code")
            if error_code == "AddingAlreadyExistsGroupUserNotSupportedError":
                mf.print_warning(f"Skipped! Identity already exists.")
            else:
                error_message = response.json().get("error", {}).get("message", str(e))
                mf.print_error(f"Failed! Error: {error_message}")
        else:
            mf.print_error(f"Failed! Error: {e}")


def connect_workspace_to_git(access_token, workspace_id, repo_org_name, repo_project_name, repo_name, repo_branch_name, repo_directory):
    """
    Connects a workspace to a Git repository in Azure DevOps.

    Args:
        access_token (str): Access token for authentication.
        workspace_id (str): Unique identifier of the workspace to connect.
        repo_org_name (str): Name of the Azure DevOps organization.
        repo_project_name (str): Name of the project within the Azure DevOps organization.
        repo_name (str): Name of the Git repository.
        repo_branch_name (str): Branch name in the repository to connect to.
        repo_directory (str): Directory within the repository to connect the workspace to.

    Returns:
        str: "OK" if the workspace is successfully connected to the Git repository.
        None: If the connection fails or if the workspace is already connected to the Git repository.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "gitProviderDetails": {
            "organizationName": repo_org_name,
            "projectName": repo_project_name,
            "gitProviderType": "AzureDevOps",
            "repositoryName": repo_name,
            "branchName": repo_branch_name,
            "directoryName": repo_directory
        }
    }

    url = f"{fabric_baseurl}/workspaces/{workspace_id}/git/connect"

    print(f"    • Connecting workspace to GIT repository {repo_name} using directory {repo_directory}... ", end="")
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        mf.print_success(f"Done!")
        return "OK"
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            mf.print_warning(f"Skipped! The workspace is already connected.")
        else:
            mf.print_error(f"Failed! Please verify git integration settings. error: {e}")
        return None


def update_workspace_from_git(access_token, workspace_id, remote_commit_hash):
    """
    Updates a workspace from a connected Git repository in Azure DevOps.

    Args:
        access_token (str): Access token for authentication.
        workspace_id (str): Unique identifier of the workspace to update.
        remote_commit_hash (str): The commit hash from the Git repository to update the workspace to.

    Returns:
        dict: JSON response from the successful update operation.
        None: If the update fails due to an error or an unresolved dependency.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "remoteCommitHash": remote_commit_hash,
        "conflictResolution": {
            "conflictResolutionType": "Workspace",
            "conflictResolutionPolicy": "PreferWorkspace"
        },
        "options": {
            "allowOverrideItems": True
        }
    }

    url = f"{fabric_baseurl}/workspaces/{workspace_id}/git/updateFromGit"

    print(f"    • Updating workspace {workspace_id} from connected GIT repository...", end="")
    
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        operation_id = response.headers.get('x-ms-operation-id')
        if operation_id is None:
            return response.json()
        else:
            get_operation_state_url = f"{fabric_baseurl}/operations/{operation_id}"

            # Poll the operation status until it's done
            while True:
                operation_state_response = requests.get(get_operation_state_url, headers=headers)
                operation_state = operation_state_response.json()
                status = operation_state.get("status")

                if status in ["NotStarted", "Running"]:
                    print(".", end="", flush=True)
                    time.sleep(5)
                elif status == "Succeeded":
                    mf.print_success(" Done!")
                    return response.json()
                else:
                    mf.print_error(" Failed! Check dependencies etc. and resolve issues inside the repository before re-initializing.")
                    return None

    except requests.exceptions.RequestException as e:
        print(f" Failed! Check dependencies etc. and resolve issues before re-initializing.")


def initialize_workspace_git_connection(access_token, workspace_id):
    """
    Initializes a Git connection for a workspace in Azure DevOps.

    Args:
        access_token (str): Access token for authentication.
        workspace_id (str): Unique identifier of the workspace to initialize the Git connection.

    Returns:
        dict: JSON response from the successful initialization operation.
        None: If the initialization fails due to a conflict or other error.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{fabric_baseurl}/workspaces/{workspace_id}/git/initializeConnection"

    print(f"    • Initializing git connection for workspace (id: {workspace_id}) ...", end="")
    
    try:
        body = {
            "initializationStrategy":"PreferRemote"
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()

        operation_id = response.headers.get('x-ms-operation-id')
        if (response.status_code == 409):
            mf.print_warning(" Skipped! Git connection already initialized.")
            return None
        if operation_id is None:
            mf.print_success(" Done!")
            return response.json()
        else:
            get_operation_state_url = f"{fabric_baseurl}/operations/{operation_id}"

            # Poll the operation status until it's done
            while True:
                operation_state_response = requests.get(get_operation_state_url, headers=headers)
                operation_state = operation_state_response.json()
                
                status = operation_state.get("Status")
                
                if status in ["NotStarted", "Running"]:
                    print(".", end="", flush=True)
                    time.sleep(5)
                elif status == "Succeeded":
                    mf.print_success(" Done!")
                    return response.json()
                else:
                    mf.print_error(" Failed!")
                    return response.json()
            
    except requests.exceptions.RequestException as e:
        mf.print_error(" Failed! Check dependencies and resolve issues inside the repository before re-initializing.")
        return None


def get_workspace_git_status(access_token, workspace_id):
    """
    Retrieves the current Git connection status for a specified workspace.

    Args:
        access_token (str): Access token for authentication.
        workspace_id (str): Unique identifier of the workspace for which to retrieve Git status.

    Returns:
        dict: JSON response with Git status information if the request is successful.
        None: If the request fails or encounters an error.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{fabric_baseurl}/workspaces/{workspace_id}/git/status"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = response.json().get("error", {}).get("message", str(e))
        return None


def get_private_endpoint_resource_type(private_link_resource_id):
    """
    Determines the resource type associated with a given private link resource ID.

    Args:
        private_link_resource_id (str): The Azure Resource ID for the private link resource.

    Returns:
        str or None: The resource type associated with the private link resource ID. Possible values include:
            - "vault" for Key Vault
            - "sqlServer" for SQL Server
            - "blob" for Blob storage
            - "databricks_ui_api" for Databricks
            - "SQL" for DocumentDB
            - "cluster" for Kusto clusters
            - "Sql" for Synapse workspaces
            - "sites" for Web Apps
            - "namespace" for Event Hubs
            - "iotHub" for IoT Hubs
            - "account" for Purview accounts
            - "amlworkspace" for Machine Learning workspaces
            - None if the resource type cannot be determined.
    """
    match private_link_resource_id:
        case _ if "Microsoft.KeyVault" in private_link_resource_id:
            return "vault"
        case _ if "Microsoft.Sql" in private_link_resource_id:
            return "sqlServer"
        case _ if "Microsoft.Storage/storageAccounts" in private_link_resource_id:
            return "blob"
        case _ if "Microsoft.Databricks" in private_link_resource_id:
            return "databricks_ui_api"
        case _ if "Microsoft.DocumentDB" in private_link_resource_id:
            return "SQL"
        case _ if "Microsoft.Kusto/clusters" in private_link_resource_id:
            return "cluster"
        case _ if "Microsoft.Synapse/workspaces" in private_link_resource_id:
            return "Sql"
        case _ if "Microsoft.Web/sites" in private_link_resource_id:
            return "sites"
        case _ if "Microsoft.EventHub/namespaces" in private_link_resource_id:
            return "namespace"
        case _ if "Microsoft.Devices/IotHubs" in private_link_resource_id:
            return "iotHub"
        case _ if "Microsoft.Purview/accounts" in private_link_resource_id:
            return "account"
        case _ if "Microsoft.MachineLearningServices/workspaces" in private_link_resource_id:
            return "amlworkspace"
        case _:
            return None


def list_managed_private_endpoionts(access_token, workspace_id, continuation_token = None):
    """
    Lists managed privated endpoints in a Microsoft Fabric workspace, supporting pagination through continuation tokens.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the workspace from which to items managed private endpoints.
        continuation_token (str, optional): A token used for paginated results. Default is None.

    Returns:
        list: A list of dictionaries representing the managed private endpoints in the workspace.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    items = []
    while True:
        # Construct the request URL
        request_url = f"{fabric_baseurl}/workspaces/{workspace_id}/managedPrivateEndpoints"
        if continuation_token is not None:
            request_url += f"&continuationToken={continuation_token}"

        response = requests.get(request_url, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            
            items.extend(response_data['value'])

            continuation_token = response_data.get('continuationToken')

            if continuation_token is None:
                break
        else:
            break

    return items


def create_workspace_managed_private_endpoint(access_token, workspace_id, endpoint_name, private_link_resource_id):
    """
    Creates a managed private endpoint within a Microsoft Fabric workspace and monitors its provisioning state until completion.

    Args:
        access_token (str): The OAuth2 bearer token used for authorization in API requests.
        workspace_id (str): The unique identifier of the workspace where the private endpoint will be created.
        endpoint_name (str): The name to assign to the managed private endpoint.
        private_link_resource_id (str): The resource ID of the target private link that the managed endpoint will connect to.

    Returns:
        dict: JSON response of the final private endpoint status if successful, or error details if provisioning fails.
        None: If the resource type cannot be identified based on the private link resource ID.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    workspace_endpoints = list_managed_private_endpoionts(access_token, workspace_id, continuation_token = None)
    endpoint = next((item for item in workspace_endpoints if item["targetPrivateLinkResourceId"] == private_link_resource_id), None)
    print(f"    • Provisioning {endpoint_name}...", end="")
    
    if endpoint:
        mf.print_warning(" Skipped! Managed private endpoint for the specified resources id already exists.")
        return endpoint
    else:
        url = f"{fabric_baseurl}/workspaces/{workspace_id}/managedPrivateEndpoints"

        resource_type = get_private_endpoint_resource_type(private_link_resource_id)

        if resource_type:
            request_message = f"Automated request for Fabric managed private endpoint {endpoint_name}"
        
            body = {
                "name": endpoint_name,
                "targetPrivateLinkResourceId": private_link_resource_id,
                "targetSubresourceType": resource_type,
                "requestMessage": request_message
                }
            
            try:
                create_response = requests.post(url, headers=headers, json=body)
                create_response.raise_for_status()
                
                private_endpoint_id = create_response.json().get("id")
                
                endpoint_url = f"{fabric_baseurl}/workspaces/{workspace_id}/managedPrivateEndpoints/{private_endpoint_id}"
                
                # Poll the private endpoint status until it's no longer in a creating/provisioning state
                while True:
                    pe_response = requests.get(endpoint_url, headers=headers)
                    pe_response.raise_for_status()
                    private_endpoint = pe_response.json()
                    
                    if private_endpoint and private_endpoint.get('provisioningState') in ["Updating", "Provisioning", "Deleting"]:
                        print(".", end="", flush=True)
                        time.sleep(10)
                    else:
                        break

                if private_endpoint and private_endpoint.get('provisioningState') == "Succeeded":
                    mf.print_success(" Done!")
                    return pe_response.json()
                else:
                    mf.print_error("Failed! Error creating private endpoint!")
                    return pe_response.json()

            except requests.exceptions.RequestException as e:
                mf.print_error(f"Failed! Please verify the resource id and that you are using a supported capacity.")
                return None
        else:
            mf.print_error("Failed! Resource type not identified based on private endpoint resource id or is not supported.")
            return None


def update_notebook_lakehouse_definition(notebook_definition, target_lakehouses):
    """
    Updates the lakehouse definition in a notebook's metadata section based on the provided target lakehouses.

    The function scans the notebook's definition for an existing lakehouse definition in the metadata section 
    (denoted by "# META") and updates it with information from the provided target lakehouses. The updated 
    metadata will include the lakehouse ID, workspace ID, and known lakehouses, if a matching lakehouse is found 
    in the target lakehouses list.

    Args:
        notebook_definition (str): The current definition of the notebook as a string, including metadata.
        target_lakehouses (list): A list of dictionaries, where each dictionary represents a lakehouse, 
                                   containing keys such as 'lakehouse_name', 'lakehouse_id', 'workspace_id', 
                                   and 'known_lakehouses'.

    Returns:
        str: The updated notebook definition, with the modified lakehouse metadata section. If no lakehouse 
             definition is found in the notebook, the original definition is returned unchanged.

    Example:
        notebook_definition = "
        # META   "dependencies": {
        # META   "lakehouse": {
        # META   "default_lakehouse_name": "Landing"
        # META   }
        # META   }
        "

        target_lakehouses = [
            {"lakehouse_name": "Landing", "lakehouse_id": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb", "workspace_id": "cccccccc-0000-1111-2222-dddddddddddd"},
            {"lakehouse_name": "Base", "lakehouse_id": "bbbbbbbb-1111-2222-3333-cccccccccccc", "workspace_id": "eeeeeeee-0000-1111-2222-eeeeeeeeeeee", "known_lakehouses": ["Curated"]}
        ]

        updated_definition = update_notebook_lakehouse_definition(notebook_definition, target_lakehouses)
        print(updated_definition)
    
    In the above example, the notebook's metadata section for "Landing" will be updated with the matching 
    lakehouse ID, workspace ID, and known lakehouses.
    """
    has_lakehouse_definition = notebook_definition.find('# META   "dependencies": {')

    if has_lakehouse_definition > -1:
        meta_end = notebook_definition.find("# META }", has_lakehouse_definition) + 10
        meta_start = notebook_definition.rfind("# META {", 0, meta_end)
        
        lakehouse_definition_raw = notebook_definition[meta_start:meta_end]
        lakehouse_definition = lakehouse_definition_raw.replace("# META", "").strip()

        json_object = json.loads(lakehouse_definition)
        
        matching_object = next(
            (lakehouse for lakehouse in target_lakehouses 
             if lakehouse.get("lakehouse_name") == json_object["dependencies"]["lakehouse"]["default_lakehouse_name"]),
            None
        )

        if matching_object:
            json_object["dependencies"]["lakehouse"]["default_lakehouse"] = matching_object.get("lakehouse_id")
            json_object["dependencies"]["lakehouse"]["default_lakehouse_workspace_id"] = matching_object.get("workspace_id")
            json_object["dependencies"]["lakehouse"]["known_lakehouses"] = matching_object.get("known_lakehouses", [])

        updated_json_string = json.dumps(json_object, indent=4)

        meta_updated_json = "\n".join([f"# META {line}" for line in updated_json_string.splitlines()])

        new_notebook_definition = (
            notebook_definition[:meta_start] +
            meta_updated_json +
            "\n\n"+
            notebook_definition[meta_end:]
        )
        return new_notebook_definition

    return notebook_definition

    
def list_items(access_token, workspace_id, item_type, continuation_token = None):
    """
    Lists items of a specific type in a Microsoft Fabric workspace, supporting pagination through continuation tokens.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the workspace from which to list items.
        item_type (str): The type of items to list (e.g., "DataPipeline", "Notebook").
        continuation_token (str, optional): A token used for paginated results. Default is None.

    Returns:
        list: A list of dictionaries representing the items in the workspace.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    items = []
    while True:
        # Construct the request URL
        request_url = f"{fabric_baseurl}/workspaces/{workspace_id}/items?type={item_type}"
        if continuation_token:
            request_url += f"&continuationToken={continuation_token}"

        response = requests.get(request_url, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            
            items.extend(response_data['value'])

            continuation_token = response_data.get('continuationToken')

            if continuation_token is None:
                break
        else:
            print(f"Error: {response.status_code}")
            print(response)
            break

    return items


def get_operation_result(access_token, operation_id):
    """
    Retrieves the result of a Microsoft Fabric operation using its operation ID.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        operation_id (str): The unique identifier of the operation whose result is to be fetched.

    Returns:
        dict or None:
            - A dictionary containing the operation result if the request is successful.
            - None if the request fails or encounters an error.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{fabric_baseurl}/operations/{operation_id}/result"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = response.json().get("error", {}).get("message", str(e))
        print(f"* Failed to get operation status: {error_details}")
        return None
    
def get_lakehouse_sqlendpoint(access_token, workspace_id, lakehouse_id):
    """
    Retrieves the SQL endpoint connection string for a specified lakehouse in a Fabric workspace.

    This function repeatedly checks the provisioning status of the SQL endpoint for the specified lakehouse 
    in the Fabric workspace. It waits until the SQL endpoint is successfully provisioned or until it fails. 
    The function returns the lakehouse details, including the connection string if the provisioning is successful.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The ID of the Fabric workspace containing the lakehouse.
        lakehouse_id (str): The ID of the lakehouse for which the SQL endpoint is being provisioned.

    Returns:
        dict: The details of the lakehouse, including the SQL endpoint connection string if successful,
              or the lakehouse details with an error message if the provisioning fails.

    Raises:
        requests.exceptions.RequestException: If an error occurs while fetching lakehouse details.
    """
    sql_endpoint_connectionstring = None
    
    print(f"      - Provisioning SQL endpoint for lakehouse...", end="")
    
    while sql_endpoint_connectionstring is None:
        lh_details = get_lakehouse(access_token, workspace_id, lakehouse_id)
        properties = lh_details.get("properties", {})
        sql_endpoint_properties = properties.get("sqlEndpointProperties")
        
        # Extract SQL endpoint details
        if sql_endpoint_properties is not None:
            if (sql_endpoint_properties.get("provisioningStatus") == "InProgress"):
                print(".", end="", flush=True)
                time.sleep(2)
            elif (sql_endpoint_properties.get("provisioningStatus") == "Failed"):
                mf.print_error(" Failed! Error provisioning SQL endpoint.")
                return lh_details
            else:
                sql_endpoint_connectionstring = sql_endpoint_properties.get("connectionString")
                mf.print_success(" Done!")
                return lh_details
        else:
            time.sleep(2)


def create_item(access_token, workspace_id, item_name, item_type, definition_base64, print_progress = False, print_output = True):
    """
    Creates a new item in a specified Microsoft Fabric workspace.

    Args:
        access_token (str): OAuth 2.0 bearer token used to authenticate the API request.
        workspace_id (str): The unique identifier of the workspace where the item will be created.
        item_name (str): The name of the item to be created in the workspace.
        item_type (str): The type of the item, such as "Lakehouse", "DataPipeline" or "Notebook".
        definition_base64 (str or None): A base64-encoded string containing the item's definition, if required. 
            If None, the definition is not included in the request.
        print_progress (bool, optional): A flag to print progress during the create operation. Default is `False`.
        print_output (bool, optional): A flag to indicate if function show print any output at all (progress or standard). Default is `True`.

    Returns:
        dict: A dictionary containing the JSON response from the API, which includes details of the newly created item.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "displayName": item_name,
        "type": item_type,
    }
    
    if definition_base64 is not None:
        item_path = ""
        if item_type == "DataPipeline":
            item_path = "pipeline-content.json"
        elif item_type == "Notebook":
            item_path = "notebook-content.py"

        body["definition"] = {
            "parts": [
                {
                    "path": item_path,
                    "payload": definition_base64,
                    "payloadType": "InlineBase64"
                }
            ]
        }
    
    print(f"    • Creating {item_type} {item_name}... ", end='') if print_progress and print_output else None

    try:
        response = requests.post(f"{fabric_baseurl}/workspaces/{workspace_id}/items", headers=headers, json=body)
        response.raise_for_status()
        operation_id = response.headers.get('x-ms-operation-id')

        if operation_id is None:
            mf.print_success("Done!" if print_progress else f"{item_type} {item_name} was successfully created.") if print_output else None
            return response.json()
        else:
            get_operation_state_url = f"{fabric_baseurl}/operations/{operation_id}"
            while True:
                operation_state_response = requests.get(get_operation_state_url, headers=headers)
                operation_state = operation_state_response.json()
                status = operation_state.get("status")
                if status in ["NotStarted", "Running"]:
                    print(".", end="", flush=True) if print_progress and print_output else None
                    time.sleep(2)
                elif status == "Succeeded":
                    mf.print_success("Done!" if print_progress else f"{item_type} {item_name} was successfully created.") if print_output else None
                    get_operation_result_url = f"{fabric_baseurl}/operations/{operation_id}/result"
                    operation_result_response = requests.get(get_operation_result_url, headers=headers)
                    return operation_result_response.json()
                else:
                    mf.print_error(f" Failed (operationsid: {operation_id})!" if print_progress else f"{item_type} {item_name} could not be created (operationsid: {operation_id}).") if print_output else None
                    return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 400:
            error_response = response.json()
            if error_response.get("errorCode") == "ItemDisplayNameAlreadyInUse":
                mf.print_warning(f" Skipped! Item already exists.") if print_output else None
                items = list_items(access_token, workspace_id, item_type)
                return next((lh for lh in items if lh['displayName'] == item_name), None)
            else:
                mf.print_error(f" Failed! Error: {http_err}") if print_output else None
        return None
    

def update_item_definition(access_token, workspace_id, item_id, item_name, item_type, definition_base64, print_progress = False):
    """
    Updates the definition of an existing item in a Microsoft Fabric workspace.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the workspace containing the item.
        item_id (str): The unique identifier of the item to update.
        item_name (str): The name of the item to be updated, used for progress reporting.
        item_type (str): The type of the item (e.g., "DataPipeline", "Notebook").
        definition_base64 (str or None): A base64-encoded string containing the item's updated definition.
            If `None`, the update will not proceed, and `None` will be returned.
        print_progress (bool, optional): A flag to print progress during the update operation. Default is `False`.

    Returns:
        dict or None: A dictionary containing the JSON response from the API with details of the updated item if successful, 
        or None if the definition is missing.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    if definition_base64 is not None:
        item_path = ""
        if item_type == "DataPipeline":
            item_path = "pipeline-content.json"
        elif item_type == "Notebook":
            item_path = "notebook-content.py"

        body = {
            "definition": {
                "parts": [
                    {
                        "path": item_path,
                        "payload": definition_base64,
                        "payloadType": "InlineBase64"
                    }
                ]
            }
        }

        if print_progress: print(f"Updating {item_type} definition for {item_name}...", end='')
    
        response = requests.post(f"{fabric_baseurl}/workspaces/{workspace_id}/items/{item_id}/updateDefinition", headers=headers, json=body)
        response.raise_for_status()
        operation_id = response.headers.get('x-ms-operation-id')

        if operation_id is None:
            print("Done!" if print_progress else f"{item_type} definition for {item_name} was successfully updated.")
            return response.json()
        else:
            get_operation_state_url = f"{fabric_baseurl}/operations/{operation_id}"
            while True:
                operation_state_response = requests.get(get_operation_state_url, headers=headers)
                operation_state = operation_state_response.json()
                status = operation_state.get("status")
                
                if status in ["NotStarted", "Running"]:
                    if print_progress: print(".", end="", flush=True)
                    time.sleep(2)
                elif status == "Succeeded":
                    print("Done!" if print_progress else f"{item_type} definition for {item_name} was successfully updated.")
                    return response.json()
                else:
                    print(f" Failed (operationsid: {operation_id})!" if print_progress else f"{item_type} definition for {item_name} could not be updated (operationsid: {operation_id}).")
                    return response.json()
    else:
        print(f"{item_type} definition for {item_name} (id:{item_id}) could not be updated. Definition is missing!")
        return None


def get_lakehouse(access_token, workspace_id, lakehouse_id):
    """
    Fetches details of a specific lakehouse from a Microsoft Fabric workspace.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the Microsoft Fabric workspace.
        lakehouse_id (str): The unique identifier of the lakehouse within the workspace.

    Returns:
        dict or None: A dictionary containing the lakehouse details if the request is successful, 
                      or None if the request fails or encounters an error.

    Raises:
        requests.exceptions.RequestException: If an error occurs during the API request.

    Example:
        lakehouse_details = get_lakehouse("your_access_token", "workspace123", "lakehouse456")
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{fabric_baseurl}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = response.json().get("error", {}).get("message", str(e))
        return None
    
def get_sqldatabase(access_token, workspace_id, database_id):
    """
    Fetches details of a specific SQL Database from a Microsoft Fabric workspace.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the Microsoft Fabric workspace.
        database_id (str): The unique identifier of the SQL Database within the workspace.

    Returns:
        dict or None: A dictionary containing the lakehouse details if the request is successful, 
                      or None if the request fails or encounters an error.

    Raises:
        requests.exceptions.RequestException: If an error occurs during the API request.

    Example:
        database_details = get_sqldatabase("your_access_token", "workspace123", "database456")
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{fabric_baseurl}/workspaces/{workspace_id}/SqlDatabases/{database_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = response.json().get("error", {}).get("message", str(e))
        return None


def create_sql_connection(access_token, connection_name, server_fqdn, database_name, tenant_id, username, password):
    """
    Creates a new connection in Microsoft Fabric/Power BI to a SQL endpoint (Fabric Database, SQL Analytics Endpoint, Azure SQL Database etc.)

    Args:
        access_token (str): OAuth 2.0 bearer token for authenticating the API request.
        connection_name (str): The name of the connection to create.
        server_fqdn (str): Fully qualified domain name/server address.
        database_name (str): Fully qualified domain name/server address.
        tenant_id (str): Tenant.
        username (str): Username / SPN App ID
        password (str): Password / SPN Secret

    Returns:
        dict or None: A dictionary containing the connection details if the connection is successfully created. 
                      Returns None if the connction already exists or if an error occurs during creation.
    """
    headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    body = {
    "connectionDetails": {
        "type": "SQL",
        "creationMethod": "SQL",
        "parameters": [
            {
                "dataType": "Text",
                "name": "server",
                "value": server_fqdn
            },
            {
                "dataType": "Text",
                "name": "database",
                "value": database_name
            }
        ]
    },
    "connectivityType": "ShareableCloud",
    "credentialDetails": {
        "singleSignOnType": "None",
        "connectionEncryption": "NotEncrypted",
        "skipTestConnection": False,
        "credentials": {
            "credentialType": "ServicePrincipal",
            "servicePrincipalClientId": username,
            "tenantId": tenant_id,
            "servicePrincipalSecret": password
        }
    },
    "displayName": connection_name,
    "privacyLevel": "Organizational"
    }

    try:
        print(f"      - Creating connection {connection_name}... ", end="")
        response = requests.post(f"{fabric_baseurl}/connections", headers=headers, json=body)
        response.raise_for_status()

        mf.print_success("Done!")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_response = response.json()
        error_code = error_response.get("errorCode", {})

        if error_code == "DuplicateConnectionName":
            mf.print_warning("Skipped! Already exists.")

            response = requests.get(f"{fabric_baseurl}/connections", headers=headers)
            data = response.json()
            connection = next((item for item in data["value"] if item["displayName"] == connection_name),None)
            
            if connection:
                connection_details = json.loads(connection["connectionDetails"])

                if connection_details['path'] == f"{server_fqdn};{database_name}":
                    print(f"      - Connection details match. Updating credentials... ", end="")
                    response = requests.post(f"{fabric_baseurl}/connections/{connection["id"]}", headers=headers, json=body)
                    response.raise_for_status()
                    #update_datasource_credentials(access_token, datasource['clusterId'], datasource['id'], tenant_id, username, password)
                    mf.print_success("Done!")
                    return connection
                else:
                    mf.print_warning("Delete & recreate! Connection details does not match")
                    role_assignments = get_connection_roleassignments(access_token, connection["id"])
                    delete_connection(access_token, connection['id'])
                    new_connection = create_sql_connection(access_token, connection_name, server_fqdn, database_name, tenant_id, username, password)
                    #Re-apply existing roleassignments
                    if role_assignments:
                        for roleassignment in role_assignments:
                            add_connection_roleassignments(access_token, new_connection.get("id"), roleassignment.get("role"), roleassignment.get("principal").get("type"), roleassignment.get("principal").get("id") )
             
                    return new_connection
            else:
                mf.print_error(f"Failed! Possible reason: Identity is not user of the datasource. Error: {http_err}")
        else:
            mf.print_error(f"Failed! Possible reason: Identity is not user of the datasource. Error: {http_err}")


def get_connection_roleassignments(access_token, connection_id):
    headers = {
           "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    response = requests.get(f"{fabric_baseurl}/connections/{connection_id}/roleAssignments", headers=headers)
    response.raise_for_status()
    return response.json()


def add_connection_roleassignments(access_token, connection_id, role, identity_type, principal_id, print_output: bool = True):
    headers = {
           "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    roleassignment = {
        "principal": {
            "id": principal_id,
            "type": identity_type
        },
        "role": role
    }

    try:
        response = requests.post(f"{fabric_baseurl}/connections/{connection_id}/roleAssignments", headers=headers, json=roleassignment)
        response.raise_for_status()
        print(f"Successfully added role assignment for principal {principal_id} as {role} to connection {connection_id}!") if print_output else None
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to add role assignment for principal {principal_id} as {role} to connection {connection_id}!") if print_output else None
        return None


def create_sql_datasource(access_token, datasource_name, server_fqdn, database_name, tenant_id, username, password):
    """
    Creates a new datasource in Microsoft Fabric/Power BI

    Args:
        access_token (str): OAuth 2.0 bearer token for authenticating the API request.
        datasource_name (str): The name of the datasource to create.
        server_fqdn (str): Fully qualified domain name/server address.
        database_name (str): Fully qualified domain name/server address.
        tenant_id (str): Tenant.
        username (str): Username.
        password (str): Password of user.

    Returns:
        dict or None: A dictionary containing the workspace details if the workspace is successfully created. 
                      Returns None if the workspace already exists or if an error occurs during creation.
    """
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    credential_value = json.dumps({
        "credentialData": [
            {"name": "servicePrincipalClientId", "value": username},
            {"name": "servicePrincipalSecret", "value": password},
            {"name": "tenantId", "value": tenant_id}
        ]
    })
            
    body = {
        "datasourceName":f"{datasource_name}",
        "datasourceType":"Sql",	
        "connectionDetails": json.dumps({
                "server": server_fqdn,
                "database": database_name
            }),		
        "singleSignOnType":"None",
        "referenceDatasource":False,
        "credentialDetails":{
            "credentialType":"ServicePrincipal",
            "credentials":credential_value,
            "encryptedConnection":"Encrypted",
            "privacyLevel":"Organizational",
            "skipTestConnection":False,
            "encryptionAlgorithm":"NONE",
            "credentialSources":[]
        },
        "allowDatasourceThroughGateway":False
        }
        
    try:
        print(f"      - Creating datasource {datasource_name}... ", end="")
        response = requests.post(f"{powerbi_baseurl_v2}/me/gatewayClusterCloudDatasource", headers=headers, json=body)
        response.raise_for_status()

        mf.print_success("Done!")
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_response = response.json()
        error_code = error_response.get("error", {}).get("code")

        if error_code == "DMTS_DuplicateDataSourceNameError":
            mf.print_warning("Skipped! Already exists.")

            response = requests.get(f"{powerbi_baseurl_v2}/me/gatewayClusterDatasources?$expand=users", headers=headers)
            data = response.json()
            datasource = next((item for item in data["value"] if item["datasourceName"] == datasource_name),None)
            
            if datasource:
                connection_details = json.loads(datasource["connectionDetails"])

                if connection_details['server'] == server_fqdn and connection_details['database'] == database_name:
                    print(f"      - Connection details match. Updating credentials... ", end="")
                    update_datasource_credentials(access_token, datasource['clusterId'], datasource['id'], tenant_id, username, password)
                    mf.print_success("Done!")
                    return datasource
                else:
                    mf.print_warning("Delete & recreate! Connection details does not match")
                    users_json = datasource.get("users")
                    delete_datasource(access_token, datasource['clusterId'], datasource['id'])
                    new_datasource = create_sql_datasource(access_token, datasource_name, server_fqdn, database_name, tenant_id, username, password)
                    #Re-apply existing datasource users
                    if users_json:
                        for user in users_json:
                            add_datasource_user(access_token, datasource.get("clusterId"), new_datasource.get("id"),
                                user.get("role","Owner"), user.get("principalType"), user.get("identifier"))
             
                    return new_datasource
            else:
                mf.print_error(f"Failed! Possible reason: Identity is not user of the datasource. Error: {http_err}")
        else:
            mf.print_error(f"Failed! Possible reason: Identity is not user of the datasource. Error: {http_err}")


def get_sql_datasource(access_token, datasource_name):
    """
    Get SQL datasource in Microsoft Fabric/Power BI by name

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        datasource_name (str): The name of the datasource to get.

    Returns:
        dict or None: A dictionary containing the datasource details
                      Returns None if the datasource does not exist.
    """
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(f"{powerbi_baseurl_v2}/me/gatewayClusterDatasources?$expand=users", headers=headers)
    data = response.json()
    datasource = next((item for item in data["value"] if item["datasourceName"] == datasource_name),None)
    return datasource


def add_datasource_user(access_token, cluster_id, datasource_id, role, identity_type, identity_identifier, print_output: bool = True):
    """
    Adds a user to a specified data source in a Power BI gateway cluster with a specified role.

    This function sends a POST request to add a user to the specified data source in the Power BI gateway cluster.
    The user is assigned a role based on the provided permission (`Admin` or `User`). The request is authenticated 
    using the provided access token. Optionally, a success or failure message is printed to the console depending on 
    the `print_output` flag.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        cluster_id (str): The ID of the gateway cluster containing the data source.
        datasource_id (str): The ID of the data source to which the user is being added.
        role (str): The permission level of the user. 
        identity_type (str): The type of identity (e.g., `User`, `Group`).
        identity_identifier (str): The identifier of the user or group being added (e.g., email address or object ID).
        print_output (bool, optional): If `True`, prints success or failure messages to the console. Defaults to `True`.

    Returns:
        dict or None: A JSON definition of the user added to the data source if successful, 
                      or `None` if an error occurs during the request.

    Raises:
        requests.exceptions.RequestException: If an error occurs while sending the HTTP request or if
                                              the API response indicates a failure.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
                
    user_definition = {
        "identifier": identity_identifier,
        "datasourceAccessRight": "Read",
        "role": role,
        "principalType": identity_type
    }

    try:
        response = requests.post(f"{powerbi_baseurl_v2}/me/gatewayClusters/{cluster_id}/datasources/{datasource_id}/users", headers=headers, json=user_definition)
        response.raise_for_status()
        print(f"Successfully added datasource user {identity_identifier} as {role} to datasource {datasource_id}!") if print_output else None
        return user_definition
    except requests.exceptions.RequestException as e:
        print(f"Failed to add datasource user {identity_identifier} as {role} to datasource {datasource_id}!") if print_output else None
        return None


def delete_datasource(access_token, cluster_id, datasource_id, print_output: bool = True):
    """
    Deletes a specified data source from a Power BI gateway cluster.

    This function sends a DELETE request to remove the specified data source from the given gateway cluster.
    The request is authenticated using the provided access token. Optionally, a success or error message
    is printed to the console depending on the `print_output` flag.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        cluster_id (str): The ID of the gateway cluster containing the data source.
        datasource_id (str): The ID of the data source to be deleted.
        print_output (bool, optional): If `True`, prints success or failure messages to the console. Defaults to `True`.

    Returns:
        None

    Raises:
        requests.exceptions.RequestException: If an error occurs while sending the HTTP request or if
                                              the API response indicates a failure.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    print(f"  → Deleting datasource with id {datasource_id}... ", end="") if print_output is True else None
    try:
        response = requests.delete(f"{powerbi_baseurl_v2}/me/gatewayClusters/{cluster_id}/datasources/{datasource_id}", headers=headers)
        response.raise_for_status()
        mf.print_success("Done!") if print_output is True else None
    except requests.exceptions.RequestException as e:
        mf.print_error(f"Failed! Error deleting datasource: {e}")

def delete_connection(access_token, connection_id, print_output: bool = True):
    """
    Deletes a specified connection in Fabric.

    This function sends a DELETE request to remove the specified connection.
    The request is authenticated using the provided access token. Optionally, a success or error message
    is printed to the console depending on the `print_output` flag.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        connection_id (str): The ID of the connection to be deleted.
        print_output (bool, optional): If `True`, prints success or failure messages to the console. Defaults to `True`.

    Returns:
        None

    Raises:
        requests.exceptions.RequestException: If an error occurs while sending the HTTP request or if
                                              the API response indicates a failure.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    print(f"  → Deleting connection with id {connection_id}... ", end="") if print_output is True else None
    try:
        response = requests.delete(f"{fabric_baseurl}/connections/{connection_id}", headers=headers)
        response.raise_for_status()
        mf.print_success("Done!") if print_output is True else None
    except requests.exceptions.RequestException as e:
        mf.print_error(f"Failed! Error deleting connection: {e}")


def update_datasource_credentials(access_token, cluster_id, datasource_id, tenant_id, username, password):
    """
    Updates the credentials for a specified data source in a Power BI gateway cluster.

    This function sends a PATCH request to update the data source credentials, using a service principal's 
    client ID, secret, and tenant ID. It authenticates the request with an access token and updates the 
    credential information for the specified cluster and data source.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        cluster_id (str): The ID of the gateway cluster containing the data source.
        datasource_id (str): The ID of the data source for which the credentials are being updated.
        tenant_id (str): The Azure AD tenant ID associated with the service principal.
        username (str): The service principal's client ID.
        password (str): The service principal's client secret.

    Returns:
        dict or None: A JSON response from the Power BI API containing the updated data source credentials
                      if successful, or `None` if an error occurs during the request.

    Raises:
        requests.exceptions.RequestException: If an error occurs while sending the HTTP request or if
                                              the API response indicates a failure.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    credential_value = json.dumps({
        "credentialData": [
            {"name": "servicePrincipalClientId", "value": username},
            {"name": "servicePrincipalSecret", "value": password},
            {"name": "tenantId", "value": tenant_id}
        ]
    })

    body = {
        "credentialDetails":{
            cluster_id:{
                "credentialType":"ServicePrincipal",
                "credentials":credential_value,
                "encryptedConnection":"Encrypted",
                "privacyLevel":"Organizational",
                "skipTestConnection":False,
                "encryptionAlgorithm":"NONE",
                "credentialSources":[]
        }}}
    
    try:
        response = requests.patch(f"{powerbi_baseurl_v2}/me/gatewayClusters/{cluster_id}/datasources/{datasource_id}/credentials", headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None


def get_capacities(access_token):
    """
    Retrieves capacities from Microsoft Power BI.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.

    Returns:
        dict or None: A dictionary containing capacities. 
                      Returns None if no capacities are found or if an error occurs.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{powerbi_baseurl}/capacities", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return None


def get_workspace_metadata(access_token, workspace_id, cluster_base_url):
    """
    Retrieves metadata from specific Microsoft Power BI workspace.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the workspace.
        cluster_base_url (str): The base URL of the Power BI cluster (this is linked to the tenant region)

    Returns:
        dict or None: A dictionary containing metadata of the specific workspace.
                      Returns None if no metadata is found or if an error occurs.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    #try:
    response = requests.get(f"{cluster_base_url}metadata/folders/{workspace_id}", headers=headers)
    response.raise_for_status()
    return response.json()
    #except requests.exceptions.RequestException as e:
    #    return None


def set_workspace_icon(access_token, workspace_id, cluster_base_url, base64_png, print_output: bool = True):
    """
    Sets the icon for a specific Microsoft Power BI workspace.

    Args:
        access_token (str): The OAuth 2.0 access token for authenticating the API request.
        workspace_id (str): The unique identifier of the workspace.
        cluster_base_url (str): The base URL of the Power BI cluster (this is linked to the tenant region)
        base64_png (str): The base64-encoded PNG image to set as the workspace icon

    Returns:
        dict or None: A dictionary containing metadata of the specific workspace.
                      Returns None if an error occurs.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"  → Uploading workspace icon... ", end="") if print_output == True else None
        icon = f"data:image/png;base64,{base64_png}"
        payload = { "icon": icon }
        
        if len(base64.b64decode(base64_png)) > 45000:
            mf.print_error("Failed! Icon size exceeds the 45KB limit.") if print_output == True else None
            return None
        
        response = requests.put(f"{cluster_base_url}metadata/folders/{workspace_id}", headers=headers, json = payload)
        response.raise_for_status()
        mf.print_success("Done!") if print_output == True else None
        return response.json()
    except requests.exceptions.RequestException as e:
        mf.print_error(f"Failed!") if print_output == True else None
        return None
    
def get_fabric_database_connection(access_token, server_fqdn, database_name):
    """
    Establishes a connection to an  Fabric SQL database using an access token for authentication.

    This function constructs an ODBC connection string for the specified server and database, encodes the
    provided access token, and attempts to connect to the database. If the connection fails, an error message
    is printed using a custom error-handling function.

    Args:
        access_token (str): The access token used for authentication to the database.
        server_fqdn (str): The fully qualified domain name (FQDN) of the server.
        database_name (str): The name of the database to connect to.

    Returns:
        pyodbc.Connection: A connection object to the specified SQL database.

    Raises:
        pyodbc.Error: If an error occurs during the connection attempt, an exception is raised.
    """

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server_fqdn};"
        f"DATABASE={database_name};"
    )

    tokenb = bytes(access_token, "UTF-8")

    exptoken = b'';
    for i in tokenb:
        exptoken += bytes({i});
        exptoken += bytes(1);
        tokenstruct = struct.pack("=i", len(exptoken)) + exptoken;

    try:
        conn = pyodbc.connect(conn_str, attrs_before = { 1256:tokenstruct});
        return conn
    except pyodbc.Error as ex:
        mf.print_error(f"Error connection to Fabric SQL Database: {ex}")


def sql_execute_nonquery(conn, sql_nonquery):
    """
    Executes a non-query SQL statement (e.g., CREATE, INSERT, UPDATE, DELETE) against a given database.

    This function creates a cursor from the provided database connection, executes the given non-query SQL statement,
    commits the transaction to persist any changes, and then closes the cursor.

    Args:
        conn (pyodbc.Connection): The connection object to the database.
        sql_nonquery (str): The SQL non-query string to be executed (e.g., CREATE TABLE, INSERT INTO, UPDATE).

    Returns:
        None
    """
    print(f"      - Running SQL script... ", end="")
    try:
        cursor = conn.cursor()
        cursor.execute(sql_nonquery)
        conn.commit()
        cursor.close()
        mf.print_success(" Done!")
    except pyodbc.DatabaseError as ex:
        mf.print_error(f"Error running non-query SQL script: {ex}")


def update_workspace_spark_settings(access_token, workspace_id, settings_definition, print_output = False):
    """
    Updates the Spark settings of a specified Microsoft Fabric workspace.

    Args:
        access_token (str): The OAuth access token for authentication.
        workspace_id (str): The unique identifier of the workspace.
        settings_definition (dict): The Spark settings to be applied to the workspace.
        print_output (bool, optional): If True, prints status messages. Defaults to False.

    Returns:
        dict or None: The JSON response from the API if successful, otherwise None.

    Raises:
        requests.exceptions.RequestException: If an error occurs during the request.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        print(f"  → Updating workspace spark settings... ", end="") if print_output == True else None
        response = requests.patch(f"{fabric_baseurl}/workspaces/{workspace_id}/spark/settings", headers=headers, json = settings_definition)
        response.raise_for_status()
        mf.print_success("Done!") if print_output == True else None
        return response.json()
    except requests.exceptions.RequestException as e:
        mf.print_error(f"Failed! Error: {e}") if print_output == True else None
        print(response.json())
        return None