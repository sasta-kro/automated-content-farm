import json
import os

if __name__ == "__main__":
    print("Do not run this file directly. This is a Util collection")




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


def display_print_ffmpeg_metadata_parameters(ffmpeg_params):
    print("      🎭 Spoofing Identity & Metadata:")

    # We want to find strings that start with ANY of these prefixes
    targets = ("encoder=", "location-eng=", "creation_time=")

    found_any = False

    for param in ffmpeg_params:
        # Check if this specific string starts with one of our targets
        if param.startswith(targets):
            # Clean up the output by removing the 'key=' part for a nicer display
            # e.g., "encoder=CapCut" -> "CapCut"
            key, value = param.split('=', 1)
            print(f"         - {key}: {value}")
            found_any = True

    print(f"         - and more ...")


    if not found_any:
        print("         (No spoofed metadata found in parameters)")



def set_debug_dir_for_modules_of_pipeline(sub_debug_dir):
    """
    Appends the passed-in argument directory to the main debug directory of the pipeline,
    so that all the debug folders stay in one place instead of having 7 different folders
    in the same folder as the code files.

    :param sub_debug_dir: specific module's sub-debug directory folder name
    :return: full debug dir path. The sub-debug dir inside the main debug folder.
    """
    main_debug_dir = "___debug_dir"
    full_debug_dir_for_specific_module = os.path.join(main_debug_dir, sub_debug_dir)

    # create the folder if it doesn't exist
    os.makedirs(full_debug_dir_for_specific_module, exist_ok=True)
    return full_debug_dir_for_specific_module

