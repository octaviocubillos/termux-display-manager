import unittest
from tdm.core.models import DisplayConfig, DisplaySession, DisplayStatus
from tdm.constants import BACKEND_TERMUX_X11, SESSION_MODE_DESKTOP

class TestModels(unittest.TestCase):
    def test_display_config_defaults(self):
        cfg = DisplayConfig()
        self.assertEqual(cfg.backend, BACKEND_TERMUX_X11)
        self.assertEqual(cfg.mode, SESSION_MODE_DESKTOP)
        self.assertEqual(cfg.display_num, 0)
        self.assertEqual(cfg.display_str, ":0")
        self.assertTrue(cfg.audio)
        self.assertFalse(cfg.virgl)

    def test_display_session_dict(self):
        cfg = DisplayConfig(resolution="1920x1080", dpi=120)
        session = DisplaySession(
            id="display-0",
            config=cfg,
            status=DisplayStatus.RUNNING,
            server_pid=1234,
            started_at=1000.0
        )
        d = session.to_dict()
        self.assertEqual(d["status"], "running")
        self.assertEqual(d["server_pid"], 1234)
        self.assertEqual(d["resolution"], "1920x1080")
        self.assertEqual(d["dpi"], 120)

if __name__ == "__main__":
    unittest.main()
