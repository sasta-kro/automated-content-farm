import json

def save_json_file(dict_or_json_data, json_file_name_path: str):
    """
    Custom function to save json file (basically a json.dump wrapper with prints)
    :param json_file_name_path:
    :param dict_or_json_data:
    :return: the path that it was saved
    """
    if dict_or_json_data:
        with open(
                json_file_name_path,
                "w",
                encoding="utf-8"
        ) as f:
            json.dump(dict_or_json_data, f, ensure_ascii=False, indent=4)
        print(f"  >>> Saved Json file to '{json_file_name_path}' ")
        return json_file_name_path

    else:
        raise ValueError(f"Couldn't save JSON. Data is empty or None. Target: {json_file_name_path}")