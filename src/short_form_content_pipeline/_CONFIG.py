import os

import yaml
from typing import Literal, Optional # import for the Optional to work (doesn't import automatically)
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Calculate Paths Globally ---
# We calculate this here so we can pass the absolute path to model_config
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up 1 levels IF in src -> Automated_content_farm
# PROJECT_ROOT_PATH = os.path.dirname(CURRENT_FILE_DIR)

# Go up 2 levels IF in short_form... -> src -> Automated_content_farm
PROJECT_ROOT_PATH = os.path.dirname(os.path.dirname(CURRENT_FILE_DIR))


DOTENV_PATH = os.path.join(PROJECT_ROOT_PATH, ".env")

# --- Defining the Shapes of Config (basically data classes for validation) ---
# ⚠️ NOTE to myself: the variable/key naming MUST match between here and the .yaml file

class ContentSettings(BaseModel):
    theme_for_persona: str
    language: str
    topic: str
    time_lengthS: str
    script_ai_model: str

class AudioSettings(BaseModel):
    tts_provider: Literal["gemini", "edge-tts"]
    speed_factor: float

class VisualSettings(BaseModel):
    bg_video_source_folder: str
    font: str
    font_size: int
    font_color: str
    stroke_width: int
    stroke_color: str

class PipelineSettings(BaseModel):
    use_mfa_alignment: bool
    clean_temp_0w0_after_run: bool





# --- The Main Config Object (singleton) ---

class Settings(BaseSettings):

    # Infrastructure (Defaults)
    PROJECT_ROOT: str = PROJECT_ROOT_PATH
    TEMP_PROCESSING_DIR: str = "___0w0__temp_automation_workspace"
    OUTPUT_DIR: str = "Final_output_videos"

    # GenAI model settings
    script_generation_temperature: float = 1.25  # High temperature = more creative/drama



    # Content Profile configs
    # These will be populated by the YAML Profile with load_profile function so it's ok to be None for now
    content: Optional[ContentSettings] = None
    audio: Optional[AudioSettings] = None
    visuals: Optional[VisualSettings] = None
    pipeline: Optional[PipelineSettings] = None

    # Secrets (Loaded from .env file with Settings)
    GEMINI_API_KEY: str

    # Load .env secrets automatically
    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding='utf-8',
        extra="ignore"
    )

    def load_profile(self, profile_name="thai_funny_story.yaml"): # default profile
        """
        Loads the YAML file and merges it into this settings object.
        REQUIRED
        """
        profile_path = os.path.join(self.PROJECT_ROOT, "Content_profiles", profile_name)

        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path, "r", encoding="utf-8") as f:
            yaml_profile_data = yaml.safe_load(f)

        # Inject YAML data into the Pydantic models
        self.content = ContentSettings(**yaml_profile_data['content'])
        self.audio = AudioSettings(**yaml_profile_data['audio'])
        self.visuals = VisualSettings(**yaml_profile_data['visuals'])
        self.pipeline = PipelineSettings(**yaml_profile_data['pipeline'])

# Initialize
SETTINGS = Settings()



# Testing (unit test?)
if __name__ == "__main__":
    SETTINGS.load_profile("thai_funny_story.yaml")
    print()
    print(f"SUCCESS: API Key loaded (starts with): {SETTINGS.GEMINI_API_KEY[:4]}***")

    ## ====== Display ===========
    # display settings option 1
    for key, value in SETTINGS:
        if key == "GEMINI_API_KEY": # exclude the API key in the print
            continue
        print(f"{key} = {value}")

    print()

    # display settings option2
    print(SETTINGS.model_dump_json(
        indent=4,
        exclude={"GEMINI_API_KEY"},
    ))


    ## =========== Access: 2 ways to access the attribute (applies in other files as well)
    # Option 1: simple static way
    language = SETTINGS.content.language
    print(language)

    # Option 1: dynamic way where the setting name (key) is not know ahead of time
    visual_settings = getattr(SETTINGS, "visuals")
    font = getattr(visual_settings, "font")
    print(font)



