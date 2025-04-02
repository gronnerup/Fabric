import requests, time
import modules.misc_functions as mf

def get_private_endpoint_api_version(private_link_resource_id):
    """
    Determines the appropriate API version for a given private link resource in Azure based on its resource type.

    Args:
        private_link_resource_id (str): The Azure Resource ID of the private link resource for which the API version is required.

    Returns:
        str: The API version string corresponding to the specified private link resource type. Returns None if the resource type
             is not recognized.

    Resource Type - API Version Mapping:
        - Microsoft.KeyVault: "2022-07-01"
        - Microsoft.Sql: "2021-11-01"
        - Microsoft.Storage/storageAccounts: "2018-02-01"
        - Microsoft.Databricks: "2024-05-01"
        - Microsoft.DocumentDB: "2024-05-01"
        - Microsoft.Kusto/clusters: "2023-08-15"
        - Microsoft.Synapse/workspaces: "2021-06-01"
        - Microsoft.Web/sites: "2024-04-01"
        - Microsoft.EventHub/namespaces: "2024-01-01"
        - Microsoft.Devices/IotHubs: "2023-06-30"
        - Microsoft.Purview/accounts: "2021-12-01"
        - Microsoft.MachineLearningServices/workspaces: "2024-04-01"
    """
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

def list_private_endpoints(access_token, private_link_resource_id):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    api_version = get_private_endpoint_api_version(private_link_resource_id)

    url = f"https://management.azure.com{private_link_resource_id}/privateEndpointConnections?api-version={api_version}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error if the request fails
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Could not get private endpoints: {e}")
        return None


def get_private_endpoint_by_name(access_token, private_link_resource_id, private_endpoint_connection_name):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = list_private_endpoints(access_token, private_link_resource_id)
    result = next((item for item in response["value"] if private_endpoint_connection_name in item["name"]), None)
    return result

def approve_private_endpoint(access_token, private_link_resource_id, private_endpoint_connection_name):
    """
    Approves a private endpoint connection within Azure, updating its status to "Approved" through an automated API request.
    
    Args:
        access_token (str): The OAuth 2.0 bearer token used for authorization in API requests.
        private_link_resource_id (str): The Azure Resource ID of the target private link resource associated with the private endpoint connection.
        private_endpoint_connection_name (str): The name of the specific private endpoint connection to approve.
    
    Returns:
        dict: JSON response containing details of the approved private endpoint connection if the request is successful.
        None: If the approval request fails.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    api_version = get_private_endpoint_api_version(private_link_resource_id)

    url = f"https://management.azure.com{private_link_resource_id}/privateEndpointConnections/{private_endpoint_connection_name}?api-version={api_version}"

    body = {
        "properties": {
            "privateLinkServiceConnectionState": {
                "status": "Approved",
                "description": "Approved by automated flow."
            }
        }
    }

    try:
        response = requests.put(url, headers=headers, json=body)
        response.raise_for_status()  # Raise an error if the request fails
        mf.print_success("Done!")
        return response.json()
    except requests.exceptions.RequestException as e:
        mf.print_error(f"Failed! Could not update private endpoint.")
        return None