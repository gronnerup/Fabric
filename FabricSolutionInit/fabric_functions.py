from azure.identity import InteractiveBrowserCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient

import requests
import json
import time 
import os

fabric_baseurl = "https://api.fabric.microsoft.com/v1"
powerbi_baseurl = "https://api.powerbi.com/v1.0/myorg"

def get_credentials_from_file(file_name):
    """
    Loads credentials from a specified JSON file located in the same directory as the script.

    Parameters:
    ----------
    file_name : str
        The name of the JSON file containing the credentials.

    Returns:
    -------
    dict
        A dictionary containing the credentials as key-value pairs.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, file_name)
    with open(file_path, "r") as file:
        return json.load(file)

def create_credentials_from_user():
    """
    Creates a ResourceManagementClient instance for Azure resources using 
    InteractiveBrowserCredential for authentication.
    """

    credential = InteractiveBrowserCredential()
    return credential

def get_access_token_from_credentials(credential : InteractiveBrowserCredential, resource):
    """
    Creates a ResourceManagementClient instance for Azure resources using 
    InteractiveBrowserCredential for authentication.

    Parameters:
    ----------
    credential : dict
        The InteractiveBrowserCredential for the user authenticated.
    resource : str
        The URI of the resource for which the access token is requested, e.g., "https://management.azure.com/" for Azure Management APIs.

    Returns:
    -------
    str
        The access token string used to authenticate requests to the specified resource.
    """
    return credential.get_token(resource).token


def get_access_token(tenant_id, client_id, client_secret, resource):
    """
    Obtains an OAuth 2.0 access token for authenticating with Azure, Power BI or Fabric services.

    Parameters:
    ----------
    tenant_id : str
        The Azure AD tenant ID where the application is registered.
    client_id : str
        The client (application) ID of the registered Azure AD application.
    client_secret : str
        The client secret of the registered Azure AD application.
    resource : str
        The URI of the resource for which the access token is requested, e.g., "https://management.azure.com/" for Azure Management APIs.

    Returns:
    -------
    str
        The access token string used to authenticate requests to the specified resource.

    """

    request_access_token_uri = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': resource
    }

    # Make the POST request to Azure AD
    response = requests.post(request_access_token_uri, data=payload,headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    # Raise an exception if the request failed
    response.raise_for_status()
    
    # Parse the JSON response to get the access token
    token = response.json().get('access_token')
    
    return token  # Return the access token


def get_workspace_by_name(access_token, workspace_name):
    """
    Retrieves a workspace by its name from Microsoft Power BI.

    Parameters:
    ----------
    headers : dict
        A dictionary containing the authorization header, including an OAuth 2.0 bearer token.
    workspace_name : str
        The name of the workspace to retrieve.

    Returns:
    -------
    dict or None
        A dictionary containing the details of the first workspace found with the specified name. 
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
        print(f"Error fetching workspace by name: {e}")
        return None
    

def create_workspace(access_token, workspace_name, workspace_description):
    """
    Creates a new workspace in Microsoft Fabric if a workspace with the specified name does not already exist.

    Parameters
    ----------
    access_token : str
        OAuth 2.0 bearer token for authenticating the API request.
    workspace_name : str
        The name of the workspace to create.
    workspace_description : str
        A description for the new workspace.

    Returns
    -------
    dict or None
        Returns a dictionary containing the workspace details if the workspace is successfully created.
        Returns None if the workspace already exists or if an error occurs during creation.

    """
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    workspace = get_workspace_by_name(access_token, workspace_name)

    if workspace is None:
        body = {
            "displayName": workspace_name,
            "description": workspace_description
        }
        try:
            response = requests.post(f"{fabric_baseurl}/workspaces", headers=headers, json=body)
            response.raise_for_status()
            print(f"Workspace {workspace_name} (id: {response.json()['id']}) was succesfully created.")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating workspace: {e}")
            return None
    else:
        print(f"Workspace {workspace_name} already exists.")
        return None


def assign_workspace_to_capacity(access_token, workspace_id, capacity_id):
    """
    Assigns a specified workspace to a given capacity in Power BI.

    Parameters:
    ----------
    access_token : str
        The OAuth 2.0 access token for authenticating the API request.
    workspace_id : str
        The unique identifier of the workspace to assign to the capacity.
    capacity_id : str
        The unique identifier of the capacity to which the workspace will be assigned.

    Returns:
    -------
    None
        Prints a confirmation message if successful or an error message if the assignment fails.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "capacityId": capacity_id
    }

    try:
        response = requests.post(f"{powerbi_baseurl}/groups/{workspace_id}/AssignToCapacity", headers=headers, json=body)
        response.raise_for_status()
        print(f"Workspace {workspace_id} assigned to capacity {capacity_id}.")
    except requests.exceptions.RequestException as e:
        print(f"Could not assign workspace to capacity. Error: {e}")


def delete_workspace(access_token, workspace_id):
    """
    Removes a specified workspace from Microsoft Power BI.

    Parameters:
    ----------
    access_token : str
        OAuth 2.0 bearer token used to authenticate the API request.
    workspace_id : str
        The unique identifier of the workspace to be removed.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{powerbi_baseurl}/groups/{workspace_id}"

    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        print(f"Workspace with id {workspace_id} was succesfully removed.")
    except requests.exceptions.RequestException as e:
        error_details = response.json().get("error", {}).get("message", str(e))
        print(f"Failed to remove workspace ({workspace_id}): {error_details}")


def create_fabric_item(access_token, workspace_id, item_name, item_type, definition_base64):
    """
    Creates a new item in a specified Microsoft Fabric workspace.

    Parameters:
    ----------
    access_token : str
        OAuth 2.0 bearer token used to authenticate the API request.
    workspace_id : str
        The unique identifier of the workspace where the item will be created.
    item_name : str
        The name of the item to be created in the workspace.
    item_type : str
        The type of the item, such as "Lakehouse", "DataPipeline" or "Notebook".
    definition_base64 : str or None
        A base64-encoded string containing the item's definition, if required. 
        If None, the definition is not included in the request.

    Returns:
    -------
    dict
        A dictionary containing the JSON response from the API, which includes details of the newly created item.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "displayName": item_name,
        "type": item_type,
    }
    
    if not definition_base64 is None:
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
    
    response = requests.post(f"{fabric_baseurl}/workspaces/{workspace_id}/items", headers=headers, json=body)
    print(f"{item_type} {item_name} was successfully created.")
    return response.json()


def update_fabric_item_definition(access_token, workspace_id, item_id, item_type, definition_base64):
    """
    Updates the definition of an existing item in a Microsoft Fabric workspace.

    Parameters:
    ----------
    access_token : str
        The OAuth 2.0 access token for authenticating the API request.
    workspace_id : str
        The unique identifier of the workspace containing the item.
    item_id : str
        The unique identifier of the item to update.
    item_type : str
        The type of the item (e.g., "DataPipeline" or "Notebook").
    definition_base64 : str or None
        A base64-encoded string containing the item's updated definition. If None, the update will not proceed.

    Returns:
    -------
    dict or None
        A dictionary containing the JSON response from the API with details of the updated item if successful, 
        or None if the definition is missing.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    if not definition_base64 is None:
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
    
        response = requests.post(f"{fabric_baseurl}/workspaces/{workspace_id}/items/{item_id}/updateDefinition", headers=headers, json=body)
        print(f"Definition for {item_type}, id:{item_id} was successfully updated.")
        return response.json()
    else:
        print(f"Definition for {item_type}, id:{item_id} could not be updated. Definition is missing!")
        return None


def add_workspace_user(access_token, workspace_id, access_role, identity_type, identity_identifier):
    """
    Assigns a specified access role to a user or group within a Power BI workspace.

    Parameters:
    ----------
    access_token : str
        The OAuth access token used to authorize the API request.
    workspace_id : str
        The unique identifier of the Power BI workspace to which the role assignment applies.
    access_role : str
        The role to assign to the user or group. Acceptable values are "Admin", "Contributor", "Member", "Viewer" or "None".
    identity_type : str
        The type of identity being assigned. Acceptable values are "User" (for email-based identification) 
        and "Group" or "App" for Entra ID groups or service principals.
    identity_identifier : str
        The identifier for the identity. For "User", this should be an email address; for other types, this should be 
        a unique identifier.
    """

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    if identity_type == "User":
        body = {
            "emailAddress": identity_identifier,
            "groupUserAccessRight": access_role
        }
    else:
        body = {
        "identifier": identity_identifier,
        "groupUserAccessRight": access_role,
        "principalType": identity_type
    }

    try:
        response = requests.post(f"{powerbi_baseurl}/groups/{workspace_id}/users", headers=headers, json=body)
        response.raise_for_status()
        print(f"Workspace role assignment updated for workspace {workspace_id}. Added {identity_type} {identity_identifier} as {access_role}.")
    except requests.exceptions.RequestException as e:
        # Attempt to extract error message from the response
        if response is not None:
            error_message = response.json().get("error", {}).get("message", str(e))
            print(f"Request failed: {error_message}")
        else:
            print(f"Request failed: {e}")


def connect_workspace_to_git(access_token, workspace_id, repo_org_name, repo_project_name, repo_name, repo_branch_name, repo_directory):
    """
    Connect a workspace to a Git repository in Azure DevOps.

    Parameters:
    -----------
    access_token : str
        Access token for authentication.
    workspace_id : str
        Unique identifier of the workspace to connect.
    repo_org_name : str
        Name of the Azure DevOps organization.
    repo_project_name : str
        Name of the project within the Azure DevOps organization.
    repo_name : str
        Name of the Git repository.
    repo_branch_name : str
        Branch name in the repository to connect to.
    repo_directory : str
        Directory within the repository to connect the workspace to.

    Returns:
    --------
    str
        "OK" if the workspace is successfully connected to the Git repository.
    None
        If the connection fails or if the workspace is already connected to the Git repository.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Build body for connecting workspace to GIT
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

    try:
        # Make the POST request to connect the workspace to GIT
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        print(f"* Workspace {workspace_id} connected to GIT repository {repo_name} using directory {repo_directory}.")
        return "OK"
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f"* The workspace {workspace_id} is already connected to the Git repository.")
        else:
            print(f"* Could not connect workspace to Git. Error: {e}")
        return None

# Function to update the workspace from GIT repository
def update_workspace_from_git(access_token, workspace_id, remote_commit_hash):
    """
    Update a workspace from a connected Git repository in Azure DevOps.

    Parameters:
    -----------
    access_token : str
        Access token for authentication.
    workspace_id : str
        Unique identifier of the workspace to update.
    remote_commit_hash : str
        The commit hash from the Git repository to update the workspace to.

    Returns:
    --------
    dict
        JSON response from the successful update operation.
    None
        If the update fails due to an error or an unresolved dependency.
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

    try:
        print(f"* Updating workspace {workspace_id} from connected GIT repository...", end="")
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
                    print(" Done!")
                    return response.json()
                else:
                    print(" Failed!")
                    print("* Update workspace from git failed. Check dependencies etc. and resolve issues inside the repository before re-initializing.")
                    return None

    except requests.exceptions.RequestException as e:
        #error_details = response.json().get("error", {}).get("message", str(e))
        print(f" Failed! Check dependencies etc. and resolve issues before re-initializing.")


def initialize_workspace_git_connection(access_token, workspace_id):
    """
    Initialize a Git connection for a workspace in Azure DevOps.

    Parameters:
    -----------
    access_token : str
        Access token for authentication.
    workspace_id : str
        Unique identifier of the workspace to initialize the Git connection.

    Returns:
    --------
    dict
        JSON response from the successful initialization operation.
    None
        If the initialization fails due to a conflict or other error.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{fabric_baseurl}/workspaces/{workspace_id}/git/initializeConnection"

    try:
        print(f"* Initializing git connection for workspace (id: {workspace_id}) ...", end="")
        body = {
            "initializationStrategy":"PreferRemote"
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()

        operation_id = response.headers.get('x-ms-operation-id')
        if (response.status_code == 409):
            print(" Conflict - Git connection already initialized.")
            return None
        if operation_id is None:
            print(" Done!")
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
                    print(" Done!")
                    return response.json()
                else:
                    print(" Failed!")
                    return response.json()
            
    except requests.exceptions.RequestException as e:
        print(e)
        print(f"* Failed to initialize git connection. Check dependencies and resolve issues inside the repository before re-initializing.")
        return None


def get_workspace_git_status(access_token, workspace_id):
    """
    Retrieve the current Git connection status for a specified workspace.

    Parameters:
    -----------
    access_token : str
        Access token for authentication.
    workspace_id : str
        Unique identifier of the workspace for which to retrieve Git status.

    Returns:
    --------
    dict
        JSON response with Git status information if the request is successful.
    None
        If the request fails or encounters an error.
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
        print(f"* Failed to get workspace Git status: {error_details}")
        return None


def get_private_endpoint_resource_type(private_link_resource_id):
    match private_link_resource_id:
        case _ if "Microsoft.KeyVault" in private_link_resource_id:
            resource_type = "vault"
        case _ if "Microsoft.Sql" in private_link_resource_id:
            resource_type = "sqlServer"
        case _ if "Microsoft.Storage/storageAccounts" in private_link_resource_id:
            resource_type = "blob"
        case _ if "Microsoft.Databricks" in private_link_resource_id:
            resource_type = "databricks_ui_api"
        case _ if "Microsoft.DocumentDB" in private_link_resource_id:
            resource_type = "SQL"
        case _ if "Microsoft.Kusto/clusters" in private_link_resource_id:
            resource_type = "cluster"
        case _ if "Microsoft.Synapse/workspaces" in private_link_resource_id:
            resource_type = "Sql"
        case _ if "Microsoft.Web/sites" in private_link_resource_id:
            resource_type = "sites"
        case _ if "Microsoft.EventHub/namespaces" in private_link_resource_id:
            resource_type = "namespace"
        case _ if "Microsoft.Devices/IotHubs" in private_link_resource_id:
            resource_type = "iotHub"
        case _ if "Microsoft.Purview/accounts" in private_link_resource_id:
            resource_type = "account"
        case _ if "Microsoft.MachineLearningServices/workspaces" in private_link_resource_id:
            resource_type = "amlworkspace"
        case _:
            resource_type = None
    
    return resource_type

def get_private_endpoint_api_version(private_link_resource_id):
    match private_link_resource_id:
        case _ if "Microsoft.KeyVault" in private_link_resource_id:
            api_version = "2022-07-01"
        case _ if "Microsoft.Sql" in private_link_resource_id:
            api_version = "2021-11-01"
        case _ if "Microsoft.Storage/storageAccounts" in private_link_resource_id:
            api_version = "2018-02-01"
        case _ if "Microsoft.Databricks" in private_link_resource_id:
            api_version = "2024-05-01"
        case _ if "Microsoft.DocumentDB" in private_link_resource_id:
            api_version = "2024-05-01"
        case _ if "Microsoft.Kusto/clusters" in private_link_resource_id:
            api_version = "2023-08-15"
        case _ if "Microsoft.Synapse/workspaces" in private_link_resource_id:
            api_version = "2021-06-01"
        case _ if "Microsoft.Web/sites" in private_link_resource_id:
            api_version = "2024-04-01"
        case _ if "Microsoft.EventHub/namespaces" in private_link_resource_id:
            api_version = "2024-01-01"
        case _ if "Microsoft.Devices/IotHubs" in private_link_resource_id:
            api_version = "2023-06-30"
        case _ if "Microsoft.Purview/accounts" in private_link_resource_id:
            api_version = "2021-12-01"
        case _ if "Microsoft.MachineLearningServices/workspaces" in private_link_resource_id:
            api_version = "2024-04-01"
        case _:
            api_version = None
    
    return api_version

def create_workspace_managed_private_endpoint(access_token, workspace_id, endpoint_name, private_link_resource_id):
    """
    Creates a managed private endpoint within a Microsoft Fabric workspace and monitors its provisioning state until completion.
    
    Parameters:
    -----------
    access_token : str
        The OAuth2 bearer token used for authorization in API requests.
    workspace_id : str
        The unique identifier of the workspace where the private endpoint will be created.
    endpoint_name : str
        The name to assign to the managed private endpoint.
    private_link_resource_id : str
        The resource ID of the target private link that the managed endpoint will connect to.

    Returns:
    -----------
    dict 
        JSON response of the final private endpoint status if successful, or error details if provisioning fails.
    None
        If the resource type cannot be identified based on the private link resource ID.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = f"{fabric_baseurl}/workspaces/{workspace_id}/managedPrivateEndpoints"

    # Automatically determine resource_type based on private_link_resource_id
    resource_type = get_private_endpoint_resource_type(private_link_resource_id)

    if resource_type:
        request_message = f"Automated request for Fabric managed private endpoint {endpoint_name}"
    
        # Build body for creating workspace managed private endpoint
        body = {
            "name": endpoint_name,
            "targetPrivateLinkResourceId": private_link_resource_id,
            "targetSubresourceType": resource_type,
            "requestMessage": request_message
            }
        
        try:
            # Make POST request to create private endpoint
            create_response = requests.post(url, headers=headers, json=body)
            create_response.raise_for_status()  # Check if the request was successful
            
            private_endpoint_id = create_response.json().get("id")
            print(f"Private endpoint {endpoint_name} is being provisioned in workspace {workspace_id}", end="")

            endpoint_url = f"{fabric_baseurl}/workspaces/{workspace_id}/managedPrivateEndpoints/{private_endpoint_id}"
            
            # Poll the private endpoint status until it's no longer in a creating/provisioning state
            while True:
                pe_response = requests.get(endpoint_url, headers=headers)
                pe_response.raise_for_status()
                private_endpoint = pe_response.json()
                
                # Check if provisioning state is still in progress (not Failed nor Succeeded)
                if private_endpoint and private_endpoint.get('provisioningState') in ["Updating", "Provisioning", "Deleting"]:
                    print(".", end="", flush=True)
                    time.sleep(10)
                else:
                    break

            # Check the final provisioning state
            if private_endpoint and private_endpoint.get('provisioningState') == "Succeeded":
                print(" Done!")
                return pe_response.json()
            else:
                print("Error creating private endpoint!")
                return pe_response.json()

        except requests.exceptions.RequestException as e:
            print(f"Could not create private endpoint {endpoint_name} in workspace {workspace_id}. {e}")
            return create_response.json()
    else:
        print("Resource type not identified based on private endpoint resource id. Skipping creation of workspace managed private endpoint.")
        return None

def get_private_endpoint_connection(access_token, private_link_resource_id, private_endpoint_identifier):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    api_version = get_private_endpoint_api_version(private_link_resource_id)
    
    url = f"https://management.azure.com{private_link_resource_id}/privateEndpointConnections?api-version={api_version}"
    
    # Send GET request to retrieve endpoint connections
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error if the request fails
    endpoint_connections = response.json().get("value", [])

    # Filter connections by name
    return [connection for connection in endpoint_connections if private_endpoint_identifier in connection.get("name", "")]


def approve_private_endpoint(access_token, private_link_resource_id, private_endpoint_connection_name):
    """
    Approves a private endpoint connection within Azure, updating its status to "Approved" through an automated API request.
    
    Parameters:
    -----------
    access_token : str
        The OAuth2 bearer token used for authorization in API requests.
    private_link_resource_id : str 
        The resource ID of the target private link resource associated with the private endpoint connection.
    private_endpoint_connection_name : str
        The name of the specific private endpoint connection to approve.
    
    Returns:
    dict
        JSON response containing details of the approved private endpoint connection if successful.
    None 
        If the approval request fails.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    api_version = get_private_endpoint_api_version(private_link_resource_id)

    # Define the URL for the PUT request
    url = f"https://management.azure.com{private_link_resource_id}/privateEndpointConnections/{private_endpoint_connection_name}?api-version={api_version}"
    
    # Define the request body
    body = {
        "properties": {
            "privateLinkServiceConnectionState": {
                "status": "Approved",
                "description": "Approved by automated flow."
            }
        }
    }

    try:
        # Send PUT request to approve the private endpoint
        response = requests.put(url, headers=headers, json=body)
        response.raise_for_status()  # Raise an error if the request fails
        print("Private endpoint connection was automatically approved.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not update private endpoint: {e}")
        return None
