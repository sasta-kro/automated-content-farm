import unittest
import inspect

from src.short_form_content_pipeline._CONSTANTS import SCRIPT_GEN_USER_PROMPT
from src.short_form_content_pipeline import generate_script_text


class ScriptGenerationPromptTests(unittest.TestCase):
    def test_script_prompt_includes_language_adapted_call_to_action_instruction(self):
        user_prompt = SCRIPT_GEN_USER_PROMPT.format(
            language="Burmese",
            topic="ရယ်စရာ ရပ်ကွက်အတင်းအဖျင်း",
        )

        self.assertIn("Burmese", user_prompt)
        self.assertIn("CALL TO ACTION", user_prompt)
        self.assertIn("like/follow", user_prompt)
        self.assertIn("comment with similar experiences", user_prompt)

    def test_script_generation_does_not_append_hardcoded_thai_outro(self):
        generate_script_data_json_source = inspect.getsource(
            generate_script_text.generate_script_data_json,
        )

        self.assertNotIn("append", generate_script_data_json_source)
        self.assertNotIn("ชอบใจฝากกดไลก์", generate_script_data_json_source)


if __name__ == "__main__":
    unittest.main()
