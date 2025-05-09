# Who's Calling – Understanding Execution Context in Microsoft Fabric

This folder contains the **Fabric Data Pipeline definition** for a generic utility pipeline used to update pipeline descriptions in Microsoft Fabric. This operation triggers an update to the `"Last Modified By"` property, which can be critical for controlling execution context—particularly when running notebooks from pipelines.

## 📖 Related Blog Post

Read the full blog post explaining this issue and the rationale behind this solution on **Peer Insights**:  
👉 [Who's Calling? Understanding Execution Context in Microsoft Fabric]([https://peerinsights.hashnode.dev/automating-microsoft-fabric-extracting-identity-support-data](https://peerinsights.hashnode.dev/whos-calling))

## 🛠️ How to Use

To use this pipeline:

1. Open a blank **Data Pipeline** in Fabric.
2. Copy the contents of the pipeline definition JSON file into the new pipeline.
3. Modify the external connection reference to point to a valid **Web v2 cloud connection** in your environment.

Update the `externalReferences` section:

```json
"externalReferences": {
    "connection": "00000000-0000-0000-0000-000000000000"
}
```

⚠️ **Important:** Do **not** change the `objectId` in the pipeline JSON. Keeping the original `objectId` ensures consistency and traceability across environments.
  
## 🚀 Running the Pipeline

The pipeline is intended to be run **after deployment via a Service Principal**, to shift the `"Last Modified By"` to a specific user identity.

You can run it using any of the following methods:

- From an **Azure DevOps pipeline**
- As part of a **GitHub Action**
- **Manually via the Fabric CLI** using the `job run` command
- Via the **Fabric REST API**:  
  👉 [Run On Demand Item Job](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/run-on-demand-item-job?tabs=HTTP)

## 🧩 Parameters

The pipeline supports two input parameters. These can be used **independently** or **together** (functioning as an **OR** filter):

- `DataPipelineList`: A comma-separated list of Data Pipeline names to update.  
  **Example:**  
  `"IngestCustomers,TransformOrders"`

- `DataPipelineStartsWith`: A string that filters for pipelines whose names start with the specified prefix.  
  **Example:**  
  `"Controller"`
