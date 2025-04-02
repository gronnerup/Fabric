# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# <center>
# 
# # **Setup - Ingest**
# 
# </center>
# 
# This notebook sets up metadata-driven ingestion pipelines for ingesting data from an Azure SQL Database. 
# 
# The notebook creates both a Fabric DataPipeline connection as well as a Web v2 connection in Power BI/Fabric and creates parent/child pipelines for handling the ingest of data from an existing PowerBI/Fabric connection.
# 
# Ingest utilized metadata based on the connection to the metadata database defined in METADATA_CONNECTION_NAME.
# 
# **Steps this notebook executes:**
# - Define variables and various utility functions needed
# - Create Web and Fabric Data Pipeline connections as Cloud Connections in Fabric/Power BI
# - Add Service Principal as Owner of the created connections
# - Add parent/child ingestion pipelines based on Data Pipeline templates for ingesting data from a sample Azure SQL Database
# - Add sample controller Data Pipeline based on a template 

# CELL ********************

# Solution Name
SOLUTION_NAME = "*FabCon"

# Connection names
SOURCE_CONNECTION_NAME = "PeerInsights_BudgetApp"
METADATA_CONNECTION_NAME = "FabCon-MetadataDB [dev]"
WEB_CONNECTION_NAME = "Fabric_Web"
DATAPIPELINE_CONNECTION_NAME = "Fabric_DataPipeline"

# Templates for SQL Server ingestion and controller
TEMPLATE_PARENT = "Template_Ingest_SQLServer_Parent"
TEMPLATE_CHILD = "Template_Ingest_SQLServer_Child"
TEMPLATE_CONTROLLER = "Template_Controller"

# Layer names
PREPARE_LAYER_NAME = 'Prepare'
STORE_LAYER_NAME = 'Store'
INGEST_LAYER_NAME = 'Ingest'

# Service Principal - required when adding role assignments to cloud connections
SPN_OBJECT_ID = "10e9e0bb-f775-4f8c-be7c-3ba241775139"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

#######################################################
#                      Functions                      #
#######################################################
import sempy.fabric as fabric
import requests
import json
import base64
from sempy.fabric.exceptions import FabricHTTPException

client = fabric.FabricRestClient()

def _create_datapipeline_connection(fabric_token, connection_name):
    
    credential_value = json.dumps({
            "credentialData": [
                {"name": "accessToken", "value": fabric_token}
            ]
        })

    body = {
    "datasourceName":connection_name,
    "datasourceType":"Extension",
    "connectionDetails":"{}",
    "singleSignOnType":"None",
    "mashupTestConnectionDetails":{
        "functionName":"FabricDataPipelines.Actions",
        "moduleName":"FabricDataPipelines",
        "moduleVersion":"1.0.4",
        "parameters":[ ]
    },
    "referenceDatasource":False,
            "credentialDetails": {
                "credentialType": "OAuth2",
                "credentials": credential_value,
                "encryptedConnection": "Encrypted",
                "encryptionAlgorithm": "None",
                "privacyLevel": "None"
            },
        "allowDatasourceThroughGateway":False
    }

    print("→ Create or get DataPipeline connection... ", end="")
    try:
        response = client.post(f"https://api.powerbi.com/v2.0/myorg/me/gatewayClusterCloudDatasource", json=body)
        response.raise_for_status()
        print("Done!")
        return response.json()
    except FabricHTTPException as e:
        if "DMTS_DuplicateDataSourceNameError" in str(e):
            print("Already exists. Reusing existing.")
            return _get_connection(connection_name)
        else:
            return None


def _create_web_connection(fabric_token, connection_name):    
    credential_value = json.dumps({
            "credentialData": [
                {"name": "accessToken", "value": fabric_token}
            ]
        })

    body = {
    "datasourceName":connection_name,
    "datasourceType":"Extension",
    "connectionDetails":"{\"baseUrl\":\"https://api.fabric.microsoft.com/v1\",\"audience\":\"https://api.fabric.microsoft.com/\"}",
    "singleSignOnType":"None",
    "mashupTestConnectionDetails":{
        "functionName":"WebForPipeline.Contents",
        "moduleName":"WebForPipeline",
        "moduleVersion":"1.0.7",
        "parameters":[
            {
                "name":"baseUrl",
                "type":"text",
                "isRequired":True,
                "value":"https://api.fabric.microsoft.com/v1"
            },
            {
                "name":"audience",
                "type":"nullable text",
                "isRequired":False,
                "value":"https://api.fabric.microsoft.com/"
            }
        ]
    },
    "referenceDatasource":False,
            "credentialDetails": {
                "credentialType": "OAuth2",
                "credentials": credential_value,
                "encryptedConnection": "Encrypted",
                "encryptionAlgorithm": "None",
                "privacyLevel": "None"
            },
        "allowDatasourceThroughGateway":False
    }

    print("→ Create or get Web v2 connection... ", end="")
    try:
        response = client.post(f"https://api.powerbi.com/v2.0/myorg/me/gatewayClusterCloudDatasource", json=body)
        response.raise_for_status()
        print("Done!")
        return response.json()
    except FabricHTTPException as e:
        if "DMTS_DuplicateDataSourceNameError" in str(e):
            print("Already exists. Reusing existing.")
            return _get_connection(connection_name)
        else:
            return None


def _get_connection(connection_name):
    response = client.get(f"https://api.powerbi.com/v2.0/myorg/me/gatewayClusterDatasources?$expand=users")
    data = response.json()
    datasource = next((item for item in data["value"] if item.get("datasourceName") == connection_name), None)
    return datasource


def _add_connection_role_assignment(connection_id, principal_id, principal_type, role):
    payload = {
    "principal": {
        "id": principal_id,
        "type": principal_type
    },
    "role": role
    }

    print(f"→ Adding role assignment for {principal_type} with id {principal_id} on connection {connection_id}... ", end="")
    try:
        response = client.post(f"https://api.fabric.microsoft.com/v1/connections/{connection_id}/roleAssignments", json = payload)
        response.raise_for_status()
        print("Done!")
    except FabricHTTPException as e:
        if "ConnectionRoleAssignmentAlreadyExists" in str(e):
            print("Skipped! Role assignment already exists.")
        else:
            print("Failed!")
    

def _create_datapipeline(workspace_id, item_name, definition_base64):
    body = {
        "displayName": item_name,
        "type": "DataPipeline",
        "definition": {
            "parts": [
                {
                    "path": "pipeline-content.json",
                    "payload": definition_base64,
                    "payloadType": "InlineBase64"
                }
            ]
        }
    }

    print(f"→ Creating Data Pipeline \033[1m{item_name}\033[0m in workspace \033[1m{workspace_id}\033[0m... ", end="")
    try:
        response = client.post(f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items", json=body)
        response.raise_for_status()
        operation_id = response.headers.get('x-ms-operation-id')

        if operation_id is None:
            print("Done!")
            return response.json().get("id")
        else:
            get_operation_state_url = f"https://api.fabric.microsoft.com/v1/operations/{operation_id}"
            while True:
                operation_state_response = client.get(get_operation_state_url)
                operation_state = operation_state_response.json()
                status = operation_state.get("status")
                if status in ["NotStarted", "Running"]:
                    print(".", end="", flush=True)
                    time.sleep(2)
                elif status == "Succeeded":
                    print("Done!")
                    get_operation_result_url = f"https://api.fabric.microsoft.com/v1/operations/{operation_id}/result"
                    operation_result_response = client.get(get_operation_result_url)
                    return operation_result_response.json().get("id")
                else:
                    print("Failed!")
                    print(operation_state_response)
                    return None
    except FabricHTTPException as e:
        print(e)
        if "ItemDisplayNameAlreadyInUse" in str(e):
            print(f" Skipped! Item already exists.") 
            return fabric.resolve_item_id(item_name, "DataPipeline", workspace_id)
        else:
            print(f" Failed!")
            return None

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

METADATA_CONNECTION_NAME

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

PREPARE_WORKSPACE = fabric.get_workspace_id()
STORE_WORKSPACE = fabric.resolve_workspace_id(f"{SOLUTION_NAME} - {STORE_LAYER_NAME} [dev]") 
INGEST_WORKSPACE = fabric.resolve_workspace_id(fabric.resolve_workspace_name(PREPARE_WORKSPACE).replace(PREPARE_LAYER_NAME, INGEST_LAYER_NAME))

SOURCE_CONNECTION_ID = _get_connection(SOURCE_CONNECTION_NAME).get("id")
META_CONNECTION = _get_connection(METADATA_CONNECTION_NAME)
META_CONNECTION_ID = META_CONNECTION.get("id")
META_INITIALCATALOG = json.loads(META_CONNECTION.get("connectionDetails")).get("database")

LANDING_LAKEHOUSE = notebookutils.lakehouse.get(name="Landing", workspaceId=STORE_WORKSPACE).id

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Create Fabric DataPipeline connection + Web connection
# Create new or reuse existing Fabric DataPipeline connection and Web connection for use in Invoke Pipeline activities and Web activities in Fabric Data Factory.

# CELL ********************

TOKEN = notebookutils.credentials.getToken("https://api.fabric.microsoft.com")
DATAPIPELINE_CONNECTION = _create_datapipeline_connection(TOKEN, DATAPIPELINE_CONNECTION_NAME)
WEB_CONNECTION_ID = _create_web_connection(TOKEN, WEB_CONNECTION_NAME).get("id")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Add Service Principal identity as Owner of the created connections
# This is required as we will deploy our items using a Service Principal which must then have access to connections used in Data Pipelines.

# CELL ********************

_add_connection_role_assignment(DATAPIPELINE_CONNECTION.get('id'), SPN_OBJECT_ID, "ServicePrincipal", "Owner")
_add_connection_role_assignment(WEB_CONNECTION_ID, SPN_OBJECT_ID, "ServicePrincipal", "Owner")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Clone template parent/child Data Pipelines
# Clone template pipelines and change connections in pipelines. 
# Activate activities once definition has been manipulated.

# CELL ********************

# Child data pipeline
child_pipeline_id = fabric.resolve_item_id(TEMPLATE_CHILD, "DataPipeline", INGEST_WORKSPACE)
child_def = client.post(f"https://api.fabric.microsoft.com/v1/workspaces/{INGEST_WORKSPACE}/items/{child_pipeline_id}/getDefinition").json()
definition_base64 = next((part for part in child_def["definition"]["parts"] if part["path"] == "pipeline-content.json"), None).get("payload")

definition_bytes = base64.b64decode(definition_base64)
definition_str = definition_bytes.decode("utf-8")  # Convert bytes to string
definition_bytes = base64.b64encode(definition_str.encode("utf-8"))  
definition_base64 = definition_bytes.decode("utf-8") 

child_pipeline_name = f"Ingest - AzureSqlDb - Child"
child_pipeline_id = _create_datapipeline(INGEST_WORKSPACE, child_pipeline_name, definition_base64)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# Parent data pipeline
parent_pipeline_id = fabric.resolve_item_id(TEMPLATE_PARENT, "DataPipeline", INGEST_WORKSPACE)
parent_def = client.post(f"https://api.fabric.microsoft.com/v1/workspaces/{INGEST_WORKSPACE}/items/{parent_pipeline_id}/getDefinition").json()
definition_base64 = next((part for part in parent_def["definition"]["parts"] if part["path"] == "pipeline-content.json"), None).get("payload")

definition_bytes = base64.b64decode(definition_base64)
definition_str = definition_bytes.decode("utf-8")  # Convert bytes to string
definition_str = definition_str.replace("@SourceConnectionName", SOURCE_CONNECTION_NAME)
definition_str = definition_str.replace("@MetaConnectionID", META_CONNECTION_ID)
definition_str = definition_str.replace("@WebConnectionID", WEB_CONNECTION_ID)
definition_str = definition_str.replace("@DataPipelineConnectionID", DATAPIPELINE_CONNECTION.get("id"))
definition_str = definition_str.replace("@ChildPipelineName", child_pipeline_name)
definition_str = definition_str.replace("@MetaInitialCatalog", META_INITIALCATALOG)
definition_str = definition_str.replace("@DestinationWorkspaceID", STORE_WORKSPACE)
definition_str = definition_str.replace("@DestinationLakehouseID", LANDING_LAKEHOUSE)
definition_str = definition_str.replace("Inactive", "Active")
definition_bytes = base64.b64encode(definition_str.encode("utf-8"))  
definition_base64 = definition_bytes.decode("utf-8") 

parent_pipeline_name = f"Ingest - AzureSqlDb - Parent"
parent_pipeline_id = _create_datapipeline(INGEST_WORKSPACE, parent_pipeline_name, definition_base64)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Clone template for Controller Data Pipeline
# Clone controller pipeline change connections etc. 
# Activate activities once definition has been manipulated.

# CELL ********************

# Controller data pipeline
pipeline_id = fabric.resolve_item_id(TEMPLATE_CONTROLLER, "DataPipeline", INGEST_WORKSPACE)
pipeline_def = client.post(f"https://api.fabric.microsoft.com/v1/workspaces/{INGEST_WORKSPACE}/items/{pipeline_id}/getDefinition").json()
definition_base64 = next((part for part in pipeline_def["definition"]["parts"] if part["path"] == "pipeline-content.json"), None).get("payload")

definition_bytes = base64.b64decode(definition_base64)
definition_str = definition_bytes.decode("utf-8")  # Convert bytes to string
definition_str = definition_str.replace("@WebConnectionID", WEB_CONNECTION_ID)
definition_str = definition_str.replace("@DataPipelineConnectionID", DATAPIPELINE_CONNECTION.get("id"))
definition_str = definition_str.replace("@ParentPipelineName", parent_pipeline_name)
definition_str = definition_str.replace("@DestinationWorkspaceID", STORE_WORKSPACE)
definition_str = definition_str.replace("@DestinationLakehouseID", LANDING_LAKEHOUSE)
definition_str = definition_str.replace("@SourceConnectionName", SOURCE_CONNECTION_NAME)
definition_str = definition_str.replace("Inactive", "Active")

definition_bytes = base64.b64encode(definition_str.encode("utf-8"))  
definition_base64 = definition_bytes.decode("utf-8") 

controller_pipeline_name = f"Controller - Full"
result = _create_datapipeline(INGEST_WORKSPACE, controller_pipeline_name, definition_base64)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

print(f"\n\033[1m✅ SETUP OF INGEST PIPELINES FOR SOURCE CONNECTION {SOURCE_CONNECTION_NAME.upper()} AND BASIC CONTROLLER PIPELINE COMPLETED!\033[0m")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
