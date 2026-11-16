import io
import json
import os
from pathlib import Path
from subprocess import CompletedProcess
import unittest
from unittest.mock import patch

from demo import EXAMPLES, scene_frame
from generate_scene import generate_scene
from scene import PlayState, parse_scene


def greenhouse():
    return json.loads((EXAMPLES / "greenhouse.json").read_text(encoding="utf-8"))


class SceneTests(unittest.TestCase):
    def test_interaction_unlocks_gate_and_changes_art(self):
        scene = parse_scene(greenhouse())
        state = PlayState(scene)
        self.assertEqual(state.dialogue, scene.intro)
        idle = state.pixels(0)
        state.interact(2)
        self.assertIn("holds the iron gate shut", state.dialogue)
        self.assertEqual(state.pixels(0), idle)
        self.assertEqual(scene_frame(state, 144, 40, 0)[26][98], (255, 232, 164))
        self.assertEqual(scene_frame(state, 36, 10, 0)[6][24], (255, 232, 164))
        state.interact(0)
        self.assertIn("You take the key", state.dialogue)
        self.assertEqual(state.pixels(0)[46][35], (255, 237, 176))
        state.interact(2)
        self.assertIn("The gate swings inward", state.dialogue)
        opened = state.pixels(0)
        self.assertNotEqual(opened[47][118], idle[47][118])
        self.assertEqual(opened[46][35], (255, 237, 176))
        state.interact(2)
        self.assertEqual(state.dialogue, "The iron gate is open.")
        self.assertEqual(state.pixels(0), opened)
        state.interact(0)
        self.assertIn("already have", state.dialogue)
        self.assertEqual(state.pixels(0), opened)
        self.assertEqual(PlayState(scene).pixels(0), idle)

    def test_active_art_replaces_old_sprite_in_the_same_bounds(self):
        data = greenhouse()
        lantern = data["objects"][0]
        lantern["art"] = [["rect", "flame", 3, 4, 2, 2]]
        lantern["active_art"] = [["rect", "flame", 8, 4, 2, 2]]
        scene = parse_scene(data)
        state = PlayState(scene)
        idle = state.pixels(0)
        self.assertEqual(idle[40][28], (255, 237, 176))
        state.interact(0)
        active = state.pixels(0)
        self.assertEqual(active[40][28], scene.background[40][28])
        self.assertEqual(active[40][33], (255, 237, 176))
        self.assertEqual(scene_frame(state, 144, 40, 0)[36][25], (255, 232, 164))

    def test_version_one_still_plays_absolute_art_and_overlays(self):
        state = PlayState(parse_scene({
            "title": "Example", "intro": "An old scene.",
            "palette": {"dark": "101010", "light": "ffffff"},
            "background": [["rect", "dark", 0, 0, 144, 80]],
            "objects": [{
                "name": "Lamp", "bounds": [10, 20, 6, 6], "text": "You light the lamp.",
                "art": [["rect", "light", 11, 22, 2, 2]],
                "after": [["rect", "light", 14, 24, 1, 1]],
            }],
        }))
        self.assertEqual(state.pixels(0)[22][11], (255, 255, 255))
        self.assertEqual(state.pixels(0)[24][14], (16, 16, 16))
        state.interact(0)
        self.assertEqual(state.pixels(0)[22][11], (255, 255, 255))
        self.assertEqual(state.pixels(0)[24][14], (255, 255, 255))

    def test_polygons_fill_within_their_outline(self):
        scene = parse_scene(greenhouse())
        self.assertEqual(scene.background[16][28], (190, 217, 217))
        self.assertEqual(scene.background[16][3], (17, 24, 39))

    def test_rejects_bad_targets(self):
        for field, value, message in (
            ("bounds", [140, 70, 20, 20], "drawing bounds"),
            ("bounds", [48, 26, 30, 37], "overlap"),
            ("art", [["rect", "moon", 98, 26, 2, 2]], "drawing bounds"),
            ("active_art", [["rect", "moon", 29, 36, 2, 2]], "drawing bounds"),
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

        request.side_effect = [model_response({"version": 1}), model_response(data)]
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
        feedback = json.loads(second.data)["messages"][-1]["content"]
        self.assertIn("version 2 scene with object-local art coordinates", feedback)

    @patch.dict(os.environ, {}, clear=True)
    @patch("generate_scene.subprocess.run")
    def test_codex_is_default_without_api_settings(self, run):
        data = greenhouse()

        def codex(command, *, cwd, input, env, **_):
            self.assertEqual(command[0], "codex")
            self.assertIn("exec", command)
            self.assertEqual(command[-1], "-")
            self.assertIn("The moonlit greenhouse", input)
            self.assertNotIn("OPENAI_API_KEY", env)
            response = Path(command[command.index("--output-last-message") + 1])
            self.assertEqual(response.parent, Path(cwd))
            response.write_text("```json\n" + json.dumps(data) + "\n```", encoding="utf-8")
            return CompletedProcess(command, 0, stdout="", stderr="")

        run.side_effect = codex
        scene, returned_data = generate_scene("The moonlit greenhouse")
        self.assertEqual(scene.title, data["title"])
        self.assertEqual(returned_data, data)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "api-test", "OPENAI_BASE_URL": "https://api.test/v1"})
    @patch("generate_scene.subprocess.run")
    def test_codex_provider_uses_cli_even_with_api_settings(self, run):
        run.return_value = CompletedProcess(
            ["codex"], 1, stdout="", stderr="Error: sign in with codex login",
        )
        with self.assertRaisesRegex(ValueError, "sign in with codex login"):
            generate_scene("A greenhouse", model="codex-model", provider="codex")
        args, options = run.call_args
        self.assertEqual(args[0][-3:], ["--model", "codex-model", "-"])
        self.assertNotIn("OPENAI_API_KEY", options["env"])
        self.assertNotIn("OPENAI_BASE_URL", options["env"])
