import io
import json
import os
import unittest
from unittest.mock import patch

from demo import EXAMPLES
from generate_scene import generate_scene
from scene import PlayState, parse_scene


def greenhouse():
    return json.loads((EXAMPLES / "greenhouse.json").read_text(encoding="utf-8"))


class SceneTests(unittest.TestCase):
    def test_interaction_unlocks_gate_and_changes_art(self):
        scene = parse_scene(greenhouse())
        state = PlayState(scene)
        self.assertEqual(state.dialogue, scene.intro)
        state.interact(2)
        self.assertIn("holds the iron gate shut", state.dialogue)
        self.assertEqual(state.pixels(0)[26][98], (255, 232, 164))
        self.assertEqual(state.pixels(0)[47][118], scene.background[47][118])
        state.interact(0)
        self.assertIn("You take the key", state.dialogue)
        self.assertEqual(state.pixels(0)[46][35], (255, 237, 176))
        state.interact(2)
        self.assertIn("The gate swings inward", state.dialogue)
        self.assertNotEqual(state.pixels(0)[47][118], scene.background[47][118])
        self.assertEqual(state.pixels(0)[46][35], (255, 237, 176))
        self.assertEqual(PlayState(scene).pixels(0)[46][35], scene.background[46][35])

    def test_polygons_fill_within_their_outline(self):
        scene = parse_scene(greenhouse())
        self.assertEqual(scene.background[16][28], (190, 217, 217))
        self.assertEqual(scene.background[16][3], (17, 24, 39))

    def test_rejects_bad_targets(self):
        for field, value, message in (
            ("bounds", [140, 70, 20, 20], "drawing bounds"),
            ("art", [["rect", "moon", 0, 0, 2, 2]], "drawing bounds"),
            ("requires", "Missing object", "unknown prerequisite"),
            ("requires", "Iron gate", "cyclic"),
            ("name", "Seed tray", "unique"),
            ("text", "\x1b[2J", "printable ASCII"),
        ):
            with self.subTest(field=field):
                data = greenhouse()
                data["objects"][2][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    parse_scene(data)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "example", "OPENAI_BASE_URL": "https://example.test/v1"})
    @patch("generate_scene.urlopen")
    def test_generation_passes_prompt_and_repairs_invalid_output(self, request):
        data = greenhouse()

        def model_response(scene_json):
            payload = {"choices": [{"message": {"content": json.dumps(scene_json)}}]}
            return io.BytesIO(json.dumps(payload).encode())

        request.side_effect = [model_response({}), model_response(data)]
        prompt = "A moonlit greenhouse with a locked gate."
        scene, returned_data = generate_scene(prompt, model="scene-model")
        self.assertEqual(scene.title, data["title"])
        self.assertEqual(returned_data, data)
        first, second = [call.args[0] for call in request.call_args_list]
        self.assertEqual(first.full_url, "https://example.test/v1/chat/completions")
        self.assertEqual(first.get_header("Authorization"), "Bearer example")
        body = json.loads(first.data)
        self.assertEqual(body["messages"][1], {"role": "user", "content": prompt})
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["model"], "scene-model")
        self.assertIn("Fix this validation error", json.loads(second.data)["messages"][-1]["content"])
