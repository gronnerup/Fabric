import requests
import modules.misc_functions as mf

def create_branch(access_token:str = None, devops_org_name:str = None, devops_project_name:str = None, devops_repo_name:str = None, devops_base_branch_name:str = None, devops_new_branch_name:str = None, print_output: bool = True):
    """
    Creates a new branch in an Azure DevOps repository based on an existing branch.

    Args:
        access_token (str): Personal Access Token (PAT) for Azure DevOps authentication.
        devops_org_name (str): Name of the Azure DevOps organization.
        devops_project_name (str): Name of the Azure DevOps project.
        devops_repo_name (str): Name of the repository where the branch will be created.
        devops_base_branch_name (str): Name of the base branch to create the new branch from.
        devops_new_branch_name (str): Name of the new branch to be created.

    Returns:
        dict: JSON response from the Azure DevOps API containing details of the newly created branch.
        None: If there is an error during the branch creation process.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    devops_org_url = f"https://dev.azure.com/{devops_org_name}/"
    print(f"  → Creating DevOps branch {devops_new_branch_name} from project {devops_project_name} in organization {devops_org_name}... ", end="") if print_output else None
    
    try:
        base_branch_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/refs?filter=heads/{devops_base_branch_name}&api-version=7.0"
        base_branch_response = requests.get(base_branch_url, headers=headers)
        base_branch_response.raise_for_status()
        base_branch_data = base_branch_response.json()
        
        base_object_id = base_branch_data['value'][0]['objectId']

        new_branch_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/refs?api-version=7.0"
        body = [
            {
                "name": f"refs/heads/{devops_new_branch_name}",
                "newObjectId": base_object_id,
                "oldObjectId": "0000000000000000000000000000000000000000"
            }
        ]
                   
        new_branch_response = requests.post(new_branch_url, headers=headers, json=body)
        new_branch_response.raise_for_status()
        
        mf.print_success(f"Done!") if print_output else None
        return new_branch_response.json()
    except requests.exceptions.RequestException as e:
        error_message = e.response.json().get("message", str(e))
        mf.print_success(f"Failed!") if print_output else None
        return None


def delete_branch(access_token: str = None, devops_org_name: str = None, devops_project_name: str = None, devops_repo_name: str = None, devops_branch_name: str = None, print_output: bool = True):
    """
    Deletes a branch in an Azure DevOps repository.

    Args:
        access_token (str): Personal Access Token (PAT) for Azure DevOps authentication.
        devops_org_name (str): Name of the Azure DevOps organization.
        devops_project_name (str): Name of the Azure DevOps project.
        devops_repo_name (str): Name of the repository where the branch is located.
        devops_branch_name (str): Name of the branch to delete.

    Returns:
        dict: JSON response from the Azure DevOps API containing details of the updated (deleted) branch.
        None: If there is an error during the branch deletion process or the branch does not exists or is already deleted.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    devops_org_url = f"https://dev.azure.com/{devops_org_name}/"

    print(f"  → Deleting DevOps branch {devops_branch_name} from project {devops_project_name} in organization {devops_org_name}... ", end="") if print_output else None
    try:
        branch_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/refs?filter=heads/{devops_branch_name}&api-version=7.0"
        branch_response = requests.get(branch_url, headers=headers)
        branch_response.raise_for_status()
        branch_data = branch_response.json()
        
        if not branch_data is None and branch_data.get("count",0) > 0 :
            object_id = branch_data['value'][0]['objectId']

            delete_branch_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/refs?api-version=7.0"
            body = [
                {
                    "name": f"refs/heads/{devops_branch_name}",
                    "oldObjectId": object_id,
                    "newObjectId": "0000000000000000000000000000000000000000",
                    
                }
            ]
                    
            delete_branch_response = requests.post(delete_branch_url, headers=headers, json=body)
            delete_branch_response.raise_for_status()
            
            mf.print_success(f"Done!") if print_output else None
            return delete_branch_response.json()
        else:
            mf.print_warning(f"Skipped! No branch found.") if print_output else None
            return None
    except requests.exceptions.RequestException as e:
        error_message = e.response.json().get("message", str(e))
        mf.print_error(f"Failed!") if print_output else None
        return None


def get_pull_request(access_token, devops_org_name, devops_project_name, devops_repo_name, devops_commit_id):
    """
    Retrieves pull request details associated with a specific commit in an Azure DevOps repository.

    Args:
        access_token (str): Personal Access Token (PAT) for Azure DevOps authentication.
        devops_org_name (str): Name of the Azure DevOps organization.
        devops_project_name (str): Name of the Azure DevOps project.
        devops_repo_name (str): Name of the repository to search for pull requests.
        devops_commit_id (str): Commit ID for which the pull request is queried.

    Returns:
        dict: JSON response from the Azure DevOps API containing pull request details.
        None: If there is an error during the query process.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    devops_org_url = f"https://dev.azure.com/{devops_org_name}/"
    query_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/pullrequestquery?api-version=7.0"
    #print (f"query_url: {query_url}")
    # Create body
    body = {
        "queries": [
            {
                "items": [devops_commit_id],
                "type": "lastMergeCommit"
            }
        ]
    }
    #print (f"body: {body}")
    try:
        response = requests.post(query_url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying pull request for commit {devops_commit_id}: {str(e)}")
        return None
    

def get_branch(access_token, devops_org_name, devops_project_name, devops_repo_name, devops_branch_name):
    """
    Gets a branch in an Azure DevOps repository.

    Args:
        access_token (str): Personal Access Token (PAT) for Azure DevOps authentication.
        devops_org_name (str): Name of the Azure DevOps organization.
        devops_project_name (str): Name of the Azure DevOps project.
        devops_repo_name (str): Name of the repository where the branch is located.
        devops_branch_name (str): Name of the branch to delete.

    Returns:
        dict: JSON response from the Azure DevOps API containing details of the branch.
        None: If there is an error during the branch retrival or the branch does not exist.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    devops_org_url = f"https://dev.azure.com/{devops_org_name}/"

    try:
        branch_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/refs?filter=heads/{devops_branch_name}&api-version=7.0"
        branch_response = requests.get(branch_url, headers=headers)
        branch_response.raise_for_status()
        return branch_response.json()
    except:
        return None
    

def repository_item_exists(access_token, devops_org_name, devops_project_name, devops_repo_name, item_path):
    """
    Check if a single item exists in an Azure DevOps repository.

    Args:
        access_token (str): Personal Access Token (PAT) for Azure DevOps authentication.
        devops_org_name (str): Name of the Azure DevOps organization.
        devops_project_name (str): Name of the Azure DevOps project.
        devops_repo_name (str): Name of the repository where the branch is located.
        devops_branch_name (str): Name of the branch.
        item_path (str): The path of the file.

    Returns:
        boolean: True if file exists, False otherwise.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    devops_org_url = f"https://dev.azure.com/{devops_org_name}/"
    
    params = {
        "path": item_path,
        "api-version": "7.1"
    }

    request_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/items"
    response = requests.get(request_url, params=params, headers=headers)

    if response.status_code == 200:
        return True
    else:
        return False


def push_to_repo(access_token, devops_org_name, devops_project_name, devops_repo_name, devops_branch_name, old_object_id, item_path, item_content, item_message):
    """
    Push changes to an Azure DevOps repository.

    Args:
        access_token (str): Personal Access Token (PAT) for Azure DevOps authentication.
        devops_org_name (str): Name of the Azure DevOps organization.
        devops_project_name (str): Name of the Azure DevOps project.
        devops_repo_name (str): Name of the repository where the branch is located.
        devops_branch_name (str): Name of the branch to push to.
        old_object_id (str): Lastest commit id.
        item_path (str): The path of the file.
        item_content (str): The content of the file to push to the repository.
        push_message (str): Commit message.
        payload (dict): Dict containing payload

    Returns:
        dict: JSON response from the Azure DevOps API containing details of the push.
        None: If there is an error during the push of changes to the repository.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    devops_org_url = f"https://dev.azure.com/{devops_org_name}/"
    devops_branch_name = f"refs/heads/{devops_branch_name}"

    repo_item_exists = repository_item_exists(access_token, devops_org_name, devops_project_name, devops_repo_name, item_path)
    #print(f"repo_item_exists: {repo_item_exists}")
    change_type = "edit" if repo_item_exists == True else "add"
    
    payload = {
        "refUpdates": [ { "name": devops_branch_name, "oldObjectId": old_object_id} ],
        "commits": [
            {
                "comment": item_message,
                "changes": [
                    {
                        "changeType": change_type,
                        "item": { "path": item_path },
                        "newContent": { "content": item_content, "contentType": "rawtext" }
                    }
                ]
            }
        ]
    }

    #print(f"payload: {payload}")

    try:
        branch_url = f"{devops_org_url}{devops_project_name}/_apis/git/repositories/{devops_repo_name}/pushes?api-version=6.0"
        branch_response = requests.post(branch_url, headers=headers, json=payload)
        branch_response.raise_for_status()
        return branch_response.json()
    except requests.exceptions.RequestException as e:
        return None