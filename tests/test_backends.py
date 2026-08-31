import unittest
from tdm.core.models import DisplayConfig
from tdm.backends import create_backend, TermuxX11Backend, NoVNCBackend, VNCBackend, XRDPBackend
from tdm.constants import BACKEND_TERMUX_X11, BACKEND_NOVNC, BACKEND_VNC, BACKEND_RDP

class TestBackends(unittest.TestCase):
    def test_backend_factories(self):
        b1 = create_backend(DisplayConfig(backend=BACKEND_TERMUX_X11))
        self.assertIsInstance(b1, TermuxX11Backend)

        b2 = create_backend(DisplayConfig(backend=BACKEND_NOVNC))
        self.assertIsInstance(b2, NoVNCBackend)

        b3 = create_backend(DisplayConfig(backend=BACKEND_VNC))
        self.assertIsInstance(b3, VNCBackend)

        b4 = create_backend(DisplayConfig(backend=BACKEND_RDP))
        self.assertIsInstance(b4, XRDPBackend)

    def test_termux_x11_commands(self):
        cfg = DisplayConfig(backend=BACKEND_TERMUX_X11, resolution="1080x2400", dpi=96)
        backend = TermuxX11Backend(cfg)
        cmd, env = backend.build_server_command()
        self.assertIn(":0", cmd)
        self.assertIn("DISPLAY", env)

    def test_vnc_commands(self):
        cfg = DisplayConfig(backend=BACKEND_VNC, resolution="1920x1080", dpi=96)
        backend = VNCBackend(cfg)
        cmd, env = backend.build_server_command()
        self.assertIn(":0", cmd)
        self.assertIn("1920x1080", cmd)
        self.assertIn("-rfbport", cmd)

    def test_rdp_commands(self):
        cfg = DisplayConfig(backend=BACKEND_RDP)
        backend = XRDPBackend(cfg)
        cmd, env = backend.build_server_command()
        self.assertIn("--nodaemon", cmd)
        self.assertIn("-p", cmd)

if __name__ == "__main__":
    unittest.main()
