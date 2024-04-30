import json

def load_config(file_name="config.json"):
    with open(file_name) as f:
        return json.load(f)