import json, os
import base64
from collections import OrderedDict

# Color codes
cdefault = '\033[0m'
cdefault_bold = '\033[1m'
cred = '\033[91m'
cred_bold = '\033[1;91m'
cyellow = '\033[33m'
cyellow_bold = '\033[1;33m'
cgreen = '\033[32m'
cgreen_bold = '\033[1;32m'
cblue_bold = '\033[1;34m'

def merge_json(parent, child, inherited_merge_type=1):
    """Recursively merge child JSON into parent, respecting 'merge_type' at all levels."""

    if not isinstance(parent, dict) or not isinstance(child, dict):
        return parent if inherited_merge_type == 0 else child  # Respect override type 0

    merged = parent.copy()  # Start with parent values

    # Get the merge type for this level, inherited if not set
    current_merge_type = child.get("merge_type", inherited_merge_type)

    for key, child_value in child.items():
        if key == "merge_type":
            continue  # Skip processing merge_type itself as an attribute

        parent_value = parent.get(key)

        if isinstance(parent_value, dict) and isinstance(child_value, dict):
            # Recursively merge dictionaries, ensuring the correct merge_type is used at all levels
            merged[key] = merge_json(parent_value, child_value, current_merge_type)

        elif isinstance(parent_value, list) and isinstance(child_value, list):
            if current_merge_type == 0:
                merged[key] = parent_value  # Keep parent list (No Override)
            elif current_merge_type == 2:
                # Ensure uniqueness in the list (works for objects, strings, numbers, etc.)
                merged[key] = list({json.dumps(item, sort_keys=True): item for item in parent_value + child_value}.values())
            else:
                merged[key] = child_value  # Replace list if merge_type is not 2

        else:
            # Apply merge rules for simple values
            if current_merge_type == 0:
                merged[key] = parent_value  # Keep parent value (No Override)
            else:
                merged[key] = child_value  # Replace with child

    return merged


def print_error(value, bold:bool = False):
    if bold:
        print(f"{cred_bold}{value}{cdefault}")
    else:
        print(f"{cred}{value}{cdefault}")


def print_warning(value, bold:bool = False):
    if bold:
        print(f"{cyellow_bold}{value}{cdefault}")
    else:
        print(f"{cyellow}{value}{cdefault}")


def print_success(value, bold:bool = False):
    if bold:
        print(f"{cgreen_bold}{value}{cdefault}")
    else:
        print(f"{cgreen}{value}{cdefault}")

def print_info(value:str = "", bold:bool = False, end:str = "\n"):
    if bold:
        print(f"{cdefault_bold}{value}{cdefault}", end=end)
    else:
        print(f"{value}", end=end)
        
def print_header(value):
    print("")
    print(f"{cblue_bold}#################################################################################################################################{cdefault}")
    print(f"{cblue_bold}# {value.center(125)} #{cdefault}")
    print(f"{cblue_bold}#################################################################################################################################{cdefault}")
    
        
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    else:
        print(f"Json file not found: {file_path}")


def image_to_base64(file_path):
    """
    Converts an image file to a Base64-encoded string.

    Args:
        image_path (str): The path to the PNG image file.

    Returns:
        str: The Base64-encoded string representation of the image.
    """
    if os.path.exists(file_path):
        with open(file_path, "rb") as image_file:
            base64_str = base64.b64encode(image_file.read()).decode("utf-8")
        return base64_str

def generate_yaml_string(data):
    """
    Generates a YAML-formatted string from a dictionary with properly formatted comments.

    Args:
        data (dict): The data to convert to a YAML string.

    Returns:
        str: A string containing the YAML representation of the data.
    """
    yaml_string = ""
    
    for section, items in data.items():
        yaml_string += f"{section}:\n"

        for key, value in items.items():
            # Check if there's a comment for this key in the current section
            if 'comment' in value:
                yaml_string += f"    # {value['comment']}\n"
            
            # Write the key-value pairs
            yaml_string += f"    \"{key}\":\n"
            for sub_key, sub_value in value.items():
                if sub_key != 'comment':  # Don't write the comment as part of the key-value pairs
                    yaml_string += f"        {sub_key}: {sub_value}\n"
            yaml_string += "\n"
    
    return yaml_string


def save_yaml(file_path, data):
    """
    Saves a dictionary to a YAML file with properly formatted comments.

    Args:
        file_path (str): The path to the YAML file to save.
        data (dict): The data to write to the file.

    Notes:
        Each section in the dictionary is written as a top-level YAML key. Comments for each key 
        are inserted where specified in the 'comment' field in the dictionary.
    """
    with open(file_path, 'w') as file:
        for section, items in data.items():
            file.write(f"{section}:\n")

            for key, value in items.items():
                # Check if there's a comment for this key in the current section
                if 'comment' in value:
                    file.write(f"    # {value['comment']}\n")
                
                # Write the key-value pairs
                file.write(f"    \"{key}\":\n")
                for sub_key, sub_value in value.items():
                    if sub_key != 'comment':  # Don't write the comment as part of the key-value pairs
                        file.write(f"        {sub_key}: {sub_value}\n")
                file.write("\n")

def create_parameter_yml(all_environments):
    """
    Creates and returns a dictionary structure for a YAML file.

    Args:
        all_environments (dict): Dict of all environments and their properties to be used for deriving the parameter yml file.

    Returns:
        dict: The parameter dictionary with predefined sections ('find_replace' and 'spark_pool') and their mapped items
    """
    yml_data = {
            "find_replace": {},
            "spark_pool": {}
        }
    
    # Extract first environment as primary
    primary_env = next(env for env in all_environments if all_environments[env].get("is_primary", True))
    primary_layers = all_environments[primary_env]["layers"]

    # Build output dictionary
    for layer_name, layer_data in primary_layers.items(): 
        primary_id = layer_data["workspace_id"]
        yml_data["find_replace"][primary_id] = {}
        
        for env, env_data in all_environments.items():
            if env == primary_env or not env_data:
                continue  # Skip primary environment
            
            env_layer = env_data["layers"].get(layer_name)
            if env_layer:
                yml_item = { env : env_layer["workspace_id"] }
                yml_data = add_item(yml_data, "find_replace", primary_id, yml_item, comment=f"Workspace Guids - {layer_name}")


        if "items" in layer_data:
            for item_type, items in layer_data["items"].items():
                for item in items:
                    item_id = item.get("id")
                    item_name = item.get("item_name")
                    pbi_connection_id = item.get("pbi_connection_id")
                    sql_endpoint_id = item.get("sql_endpoint_id")

                    # Add item entry at root level
                    yml_data["find_replace"][item_id] = {}

                    # Map items across environments
                    for env, env_data in all_environments.items():
                        if env == primary_env or not env_data:
                            continue # Skip primary environment

                        if layer_name in env_data.get("layers"):
                            env_layer = env_data.get("layers").get(layer_name)
                            if "items" in env_layer and item_type in env_layer["items"]:
                                for env_item in env_layer["items"][item_type]:
                                    if env_item["item_name"] == item_name:
                                        yml_item = { env : env_item["id"] }
                                        yml_data = add_item(yml_data, "find_replace", item_id, yml_item, comment=f"{item_type} Guid - {item_name}")

                                    if env_item.get("sql_endpoint_id"):
                                        yml_item = { env : env_item.get("sql_endpoint_id") }
                                        yml_data = add_item(yml_data, "find_replace", sql_endpoint_id, yml_item, comment=f"SQL Analytics Endpoint Guid - {item_name}")

                                    if env_item.get("pbi_connection_id"):
                                        yml_item = { env : env_item.get("pbi_connection_id") }
                                        yml_data = add_item(yml_data, "find_replace", pbi_connection_id, yml_item, comment=f"SQL Connection Guid - {item_name}")
                                        
    
    filtered_data = {
        key: value for key, value in yml_data.get("find_replace").items() if value
    }

    sorted_items = sorted(filtered_data.items(), key=lambda x: get_yml_item_sortorder(x[1].get("comment", "")))
    return {"find_replace": OrderedDict(sorted_items)}


def add_item(data, section, key, attributes, comment=None):
    """
    Adds a new item with attributes to a specified section of the data.

    Args:
        data (dict): The dictionary to modify.
        section (str): The section in which to add the item.
        key (str): The key for the new item.
        attributes (dict): The attributes to associate with the new item.
        comment (str, optional): A comment to add for the new item.

    Returns:
        dict: The updated dictionary.
    """
    if key:
        if section not in data or not isinstance(data[section], dict):
            data[section] = {}

        if key not in data[section] or not isinstance(data[section][key], dict):
            data[section][key] = {}

        if comment:
            attributes['comment'] = comment

        data[section][key].update(attributes)

    return data


def update_item(data, section, key, attributes):
    """
    Updates the attributes of an existing item in the specified section.

    Args:
        data (dict): The dictionary to modify.
        section (str): The section containing the item.
        key (str): The key of the item to update.
        attributes (dict): The new attributes to update the item with.

    Returns:
        dict: The updated dictionary.

    Raises:
        ValueError: If the item is not found in the specified section.
    """
    if section in data and key in data[section]:
        data[section][key].update(attributes)
    else:
        print(f"Item {key} not found in section {section}.")
    
    return data

def delete_item(data, section, key):
    """
    Deletes an item from a specified section in the dictionary.

    Args:
        data (dict): The dictionary to modify.
        section (str): The section containing the item.
        key (str): The key of the item to delete.

    Returns:
        dict: The updated dictionary.

    Raises:
        ValueError: If the item is not found in the specified section.
    """
    if section in data and key in data[section]:
        del data[section][key]
    else:
        print(f"Item {key} not found in section {section}.")
    
    return data

def add_child_attribute(data, section, key, child_key, child_value):
    """
    Adds a child attribute to an item in the specified section.

    Args:
        data (dict): The dictionary to modify.
        section (str): The section containing the item.
        key (str): The key of the item to add the child attribute to.
        child_key (str): The key for the child attribute.
        child_value (str): The value for the child attribute.

    Returns:
        dict: The updated dictionary.

    Raises:
        ValueError: If the item is not found in the specified section.
    """
    if section in data and key in data[section]:
        data[section][key][child_key] = child_value
    else:
        print(f"Item {key} not found in section {section}.")
    
    return data

def remove_child_attribute(data, section, key, child_key):
    """
    Removes a child attribute from an item in the specified section.

    Args:
        data (dict): The dictionary to modify.
        section (str): The section containing the item.
        key (str): The key of the item to remove the child attribute from.
        child_key (str): The key of the child attribute to remove.

    Returns:
        dict: The updated dictionary.

    Raises:
        ValueError: If the item or the child attribute is not found.
    """
    if section in data and key in data[section]:
        if child_key in data[section][key]:
            del data[section][key][child_key]
        else:
            print(f"Child attribute {child_key} not found in item {key}.")
    else:
        print(f"Item {key} not found in section {section}.")
    
    return data


def get_yml_item_sortorder(comment):
    if not comment:
        return 5 # Comment is None, Default
    elif "Workspace" in comment:
        return 1  # Workspace items first
    elif "Lakehouse" in comment:
        return 2  # Lakehouse items second
    elif "SQLDatabase" in comment:
        return 3  # SQLDatabase items third
    elif "Connection" in comment:
        return 4  # Connections forth
    return 5  # Default
    
