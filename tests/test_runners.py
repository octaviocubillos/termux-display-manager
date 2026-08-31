import unittest
from tdm.runners.session_builder import build_session_script
from tdm.runners.env_helper import prepare_environment

class TestRunners(unittest.TestCase):
    def test_prepare_environment(self):
        env = prepare_environment(display_num=0, desktop_id="xfce", audio=True, virgl=True)
        self.assertEqual(env["DISPLAY"], ":0")
        self.assertEqual(env["GDK_BACKEND"], "x11")
        self.assertEqual(env["PULSE_SERVER"], "127.0.0.1:19055")
        self.assertEqual(env["GALLIUM_DRIVER"], "virpipe")

    def test_session_builder(self):
        script_path = build_session_script(display_num=0, desktop_id="xfce")
        self.assertTrue(script_path.exists())
        content = script_path.read_text()
        self.assertIn("DISPLAY=:0", content)
        self.assertIn("exec", content)

if __name__ == "__main__":
    unittest.main()
