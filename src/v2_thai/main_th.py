import asyncio
import json
import os

from src.v2_thai.generate_audio_th import generate_audio_narration_file_th
from src.v2_thai.generate_script_th import generate_thai_script_data, translate_thai_content_to_eng


# Define Directories and files
TEMP_PROCESSING_DIR = "___temp_script_workspace"
os.makedirs(TEMP_PROCESSING_DIR, exist_ok=True) # create the folder


OUTPUT_DIR = ""


def main():
    """
    main function of the automated content farm
    """

    """ ========== 1. Generate Script """
    # Use "random viral story" to let Gemini be creative
    script_and_content_data_th = asyncio.run(
        generate_thai_script_data(
            topic=  "guy discovers my sister working in a brothel",
            time_length="30-45"
        )
    )

    # Save to a json file to verify script output (optional since json will just be passed as a variable)
    if script_and_content_data_th:
        with open(
                os.path.join(TEMP_PROCESSING_DIR, "current_script_data.json"),
                "w", encoding="utf-8"
        ) as f:
            json.dump(script_and_content_data_th, f, ensure_ascii=False, indent=4)
        print("\nSaved full result to 'current_script.json'")


    # translate to English so that I can understand
    if script_and_content_data_th is not None:
        asyncio.run(
            translate_thai_content_to_eng(script_and_content_data_th)
        )


    """ ========= 2. Generate Audio """
    asyncio.run(
        generate_audio_narration_file_th(
            script_data=script_and_content_data_th,
            output_folder_path=TEMP_PROCESSING_DIR,
            use_gemini=True
        )
    )



# ======== EXECUTION =====
if __name__ == "__main__":
    main()
