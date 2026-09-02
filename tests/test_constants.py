import unittest
from tdm.constants import (
    PORT_TDM_SERVER,
    PORT_TDM_SERVER_ALT,
    PORT_NOVNC_DEFAULT,
    PORT_VNC_DEFAULT,
    PORT_RDP_DEFAULT,
    PORT_PULSEAUDIO,
    BACKEND_TERMUX_X11,
    BACKEND_NOVNC,
    BACKEND_VNC,
    BACKEND_RDP,
    SESSION_MODE_DESKTOP,
    SESSION_MODE_TERMINAL,
    DEFAULT_DISPLAY_NUM,
    DEFAULT_DISPLAY_STR,
    DEFAULT_RESOLUTION,
    DEFAULT_DPI,
)
from tdm.version import get_version_info, __version__

class TestConstants(unittest.TestCase):
    def test_ports_range(self):
        self.assertEqual(PORT_TDM_SERVER, 19050)
        self.assertEqual(PORT_TDM_SERVER_ALT, 19051)
        self.assertEqual(PORT_NOVNC_DEFAULT, 19052)
        self.assertEqual(PORT_VNC_DEFAULT, 5900)
        self.assertEqual(PORT_RDP_DEFAULT, 3389)
        self.assertEqual(PORT_PULSEAUDIO, 19055)

    def test_backends_names(self):
        self.assertEqual(BACKEND_TERMUX_X11, "termux-x11")
        self.assertEqual(BACKEND_NOVNC, "novnc")
        self.assertEqual(BACKEND_VNC, "vnc")
        self.assertEqual(BACKEND_RDP, "rdp")

    def test_defaults(self):
        self.assertEqual(DEFAULT_DISPLAY_NUM, 0)
        self.assertEqual(DEFAULT_DISPLAY_STR, ":0")
        self.assertEqual(DEFAULT_RESOLUTION, "1080x2400")
        self.assertEqual(DEFAULT_DPI, 96)
        self.assertEqual(SESSION_MODE_DESKTOP, "desktop")
        self.assertEqual(SESSION_MODE_TERMINAL, "terminal")

    def test_version_info(self):
        info = get_version_info()
        self.assertEqual(info["version"], __version__)
        self.assertIn("version_code", info)
        self.assertIn("manifest_schema", info)

    def test_get_user_shell(self):
        from tdm.config import get_user_shell
        shell = get_user_shell()
        self.assertTrue(bool(shell))
        self.assertTrue("sh" in shell or "bash" in shell or "zsh" in shell)

if __name__ == "__main__":
    unittest.main()
