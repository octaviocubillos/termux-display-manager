import unittest
from unittest.mock import patch, MagicMock
from tdm.core.audio_manager import AudioManager
from tdm.constants import PORT_PULSEAUDIO

class TestAudioManager(unittest.TestCase):
    def setUp(self):
        self.audio = AudioManager(port=PORT_PULSEAUDIO)

    def test_audio_manager_defaults(self):
        self.assertEqual(self.audio.port, 19055)
        self.assertIsInstance(self.audio.is_pulseaudio_installed(), bool)

    def test_port_open_boolean(self):
        res = self.audio.is_port_open()
        self.assertIsInstance(res, bool)

    @patch("shutil.which")
    def test_is_pulseaudio_installed(self, mock_which):
        mock_which.return_value = "/usr/bin/pulseaudio"
        self.assertTrue(self.audio.is_pulseaudio_installed())

        mock_which.return_value = None
        self.assertFalse(self.audio.is_pulseaudio_installed())

if __name__ == "__main__":
    unittest.main()
