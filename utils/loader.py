import json

def parse_response(raw_response: str):
    if isinstance(raw_response, dict) and "output" in raw_response:
        return raw_response["output"]
    else:
        return str(raw_response)

def load_json(file_path):
    """Loads JSON data from a file."""
    with open(file_path, "r") as file:
        return json.load(file)
