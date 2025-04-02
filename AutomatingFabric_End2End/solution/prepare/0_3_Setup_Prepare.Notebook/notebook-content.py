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
# # **Setup - Prepare**
# 
# </center>
# 
# This notebook sets the default lakehouse on main notebooks defined below.
# 
# **Steps this notebook executes:**
# - Define variables and various utility functions needed
# - Set default lakehouse on:
#   - Landing to Base (1_AquaShack_Landing_To_Base)
#   - Base to Curated (2_AquaShack_Base_To_Curated)
#   - Base to Curated - Metadata (2_AquaShack_Base_To_Curated_Metadata)

# CELL ********************

SOLUTION_NAME = "*FabCon"
PREPARE_LAYER_NAME = 'Prepare'
STORE_LAYER_NAME = "Store"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import sempy.fabric as fabric
PREPARE_WORKSPACE = fabric.get_workspace_id()
STORE_WORKSPACE = fabric.resolve_workspace_id(f"{SOLUTION_NAME} - {STORE_LAYER_NAME} [dev]") 
LANDING_LAKEHOUSE = notebookutils.lakehouse.get(name="Landing", workspaceId=STORE_WORKSPACE).id
BASE_LAKEHOUSE = notebookutils.lakehouse.get(name="Base", workspaceId=STORE_WORKSPACE).id

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Update notebook definition to set default lakehouse in notehooks
# Updates the definition on main notebooks loading data from Landing to Base and Base to Curated.

# CELL ********************

# Landing To Base
(notebookutils
    .notebook
    .updateDefinition(
        name = "1_AquaShack_Landing_To_Base", 
        workspaceId=PREPARE_WORKSPACE,
        defaultLakehouse=LANDING_LAKEHOUSE, 
        defaultLakehouseWorkspace=STORE_WORKSPACE, 
        )
)

# Base To Curated
(notebookutils
    .notebook
    .updateDefinition(
        name = "2_AquaShack_Base_To_Curated", 
        workspaceId=PREPARE_WORKSPACE,
        defaultLakehouse=BASE_LAKEHOUSE, 
        defaultLakehouseWorkspace=STORE_WORKSPACE, 
        )
)

# Base To Curated - Metadata
(notebookutils
    .notebook
    .updateDefinition(
        name = "2_AquaShack_Base_To_Curated_Metadata", 
        workspaceId=PREPARE_WORKSPACE,
        defaultLakehouse=BASE_LAKEHOUSE, 
        defaultLakehouseWorkspace=STORE_WORKSPACE, 
        )
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

print(f"\n\033[1m✅ SETUP OF NOTEBOOK DEFAULT LAKEHOUSES COMPLETED!\033[0m")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
