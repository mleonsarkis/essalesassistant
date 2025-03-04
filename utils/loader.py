import json


def load_json(file_path):
    """Loads JSON data from a file."""
    with open(file_path, "r") as file:
        return json.load(file)
