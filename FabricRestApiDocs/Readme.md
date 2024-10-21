# Automating Microsoft Fabric: Extracting Identity Support Data

This folder contains sample notebooks and resources used in the blog post ["Automating Microsoft Fabric: Extracting Identity Support Data"](https://peerinsights.hashnode.dev/automating-microsoft-fabric-extracting-identity-support-data) from **Peer Insights**. The blog post demonstrates how to extract data from the Microsoft Fabric REST API documentation, focusing on which identities are supported by different endpoints, and how to build a semantic model using Semantic Link Labs.

## Overview

In this project, you'll learn how to:
1. Use a Microsoft Fabric Notebook to scrape the Fabric REST API documentation and extract identity support data for various APIs.
2. Create a semantic model using Semantic Link Labs to exposes the extracted data.
3. Generate a report using the semantic model to analyze and visualize the identity data.

## Prerequisites

To run these samples, you will need:
- Access to **Microsoft Fabric** and a **Lakehouse** in Fabric.
- A workspace assigned to **Fabric capacity**.
- **PySpark** and **BeautifulSoup** for web scraping.
- **Semantic Link Labs** for creating the semantic model.

## Setup

1. **Create a New Workspace**: Start by creating a new workspace in Microsoft Fabric and assign it to a Fabric capacity.
2. **Create a Lakehouse**: In the workspace, create a new Lakehouse where you will store the report.json file and run the notebooks.
3. **Upload Resources**: Upload the provided `report.json` file to the **Unmanaged Files** section of your Lakehouse.
4. **Run the Notebooks**: Import the notebooks from directory and run them to extract API documentation data, create the semantic model, and generate the report.

## How to Use

1. **Extract Identity Support Data**: The first notebook, `01-Load Fabric REST API docs.ipynb`, demonstrates how to scrape the Microsoft Fabric REST API documentation to retrieve identity support data for each API endpoint.
2. **Create a Semantic Model**: The second notebook, `02-Build Fabric Docs Semantic Model & PBI Report.ipynb`, shows how to create a blank semantic model using Semantic Link Labs and how to add tables, measures, and hierarchies to expose the scraped data. This notebook also generates the report.
3. **Generate a Report**: Use the report.json file to create a new report using the semantic model. This will allow you to analyze the data directly in Microsoft Fabric.

## Blog Post

For detailed instructions, check out the full blog post: [Automating Microsoft Fabric: Extracting Identity Support Data](https://peerinsights.hashnode.dev/automating-microsoft-fabric-extracting-identity-support-data).

## Future Updates

Stay tuned for more articles and samples on automating your Microsoft Fabric Lakehouse setup, managing CI/CD pipelines, and leveraging Fabric REST APIs for efficient data platform operations.

## License

This repository is licensed under the MIT License.
