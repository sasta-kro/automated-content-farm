import yaml
import os


# By creating a custom string type, we can assign a specific representer to it
# this gives precise control over which strings get the literal block style
class LiteralString(str):
    pass

def literal_string_presenter(dumper, data):
    """Represents a string using the literal block style '|'. """
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

# immediate config assignment
# This tells PyYAML: "Whenever you see an object of type LiteralString, use our custom function to format it."
yaml.add_representer(LiteralString, literal_string_presenter)


def handle_script_data_and_convert_to_yaml_for_QOL(
        original_script_content_data: dict,
        translated_script_content_data: dict,
        output_dir: str,
        brief_topic_description: str
):
    """
    Combines original and translated script data, adds a Quality-of-Life (QOL)
    copy-paste field for social media posts, and saves the result as a YAML file.
    """
    print("   📝 Generating QOL YAML file for social media posting...")

    # Extracting the content for the QOL field
    thai_title = original_script_content_data.get("title_text")
    thai_description = original_script_content_data.get("description_text")
    thai_hashtags = original_script_content_data.get("hashtags")

    # FIX: Use the correct 'translated_' prefixed keys for the english content.
    english_description = translated_script_content_data.get("translated_description")
    english_hashtags = translated_script_content_data.get("translated_hashtags")

    # QOL copy-paste string with two newlines between sections for easy copying.
    # A trailing newline is added to ensure PyYAML uses `|` (clip) instead of `|-` (strip).
    qol_copy_paste_string = \
        f"{thai_title}\n\n{thai_description}\n\n{thai_hashtags}\n\n{english_description}\n\n{english_hashtags}\n"

    # Wrap strings for consistent formatting
    # iterate through the dictionaries and wrap their string values in our custom
    # LiteralString class. This marks them for the custom representer.
    formatted_thai_data = {
        key: LiteralString(value) if isinstance(value, str) else value
        for key, value in original_script_content_data.items()
    }
    formatted_english_data = {
        key: LiteralString(value) if isinstance(value, str) else value
        for key, value in translated_script_content_data.items()
    }

    # final data dictionary with the QOL field at the top
    final_data_structure = {
        # also wrap the QOL string to ensure it gets the same treatment
        "QOL_copy_paste": LiteralString(qol_copy_paste_string),
        "thai": formatted_thai_data,
        "english": formatted_english_data,
    }

    # output path and save as YAML
    output_yaml_filename = f"full_QOL_script_data_{brief_topic_description}.yaml"
    full_yaml_save_location = os.path.join(output_dir, output_yaml_filename)

    with open(full_yaml_save_location, 'w', encoding='utf-8') as f:
        # `allow_unicode=True` preserves non-ASCII characters (Thai)
        # `sort_keys=False` maintains the order defined above for better readability
        # `width` is less critical now due to the custom representer but kept for safety
        yaml.dump(final_data_structure, f, allow_unicode=True, sort_keys=False, width=120)

    print(f"    QOL script data saved to: {full_yaml_save_location}")
    return full_yaml_save_location


#    debug main
import json
from src.short_form_content_pipeline.Util_functions import set_debug_dir_for_module_of_pipeline

if __name__ == "__main__":

    sub_debug_dir = "_d_handle_script_data_yaml"
    full_debug_dir = set_debug_dir_for_module_of_pipeline(sub_debug_dir)

    test_json_data = f"{full_debug_dir}/test_script_data_json.json"

    with open(test_json_data, 'r', encoding='utf-8') as f:
        full_script_data = json.load(f)

    mock_original_script_data = full_script_data.get("thai")
    mock_translated_script_data = full_script_data.get("english")

    if not mock_original_script_data or not mock_translated_script_data:
        raise ValueError("Mock data JSON is missing 'thai' or 'english' keys.")

    # mock topic
    mock_brief_topic = "husbandFartPoisoning_test"

    output_path = handle_script_data_and_convert_to_yaml_for_QOL(
        original_script_content_data=mock_original_script_data,
        translated_script_content_data=mock_translated_script_data,
        output_dir=full_debug_dir,
        brief_topic_description=mock_brief_topic
    )
    print(f"\n > Test complete. YAML file generated successfully.")
