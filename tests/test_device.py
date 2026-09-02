import unittest
from tdm.core.device_manager import device_manager

class TestDeviceManager(unittest.TestCase):
    def test_battery_status(self):
        bat = device_manager.get_battery_status()
        self.assertIsInstance(bat, dict)
        self.assertIn("percentage", bat)
        self.assertIn("status", bat)
        self.assertIn("health", bat)
        self.assertIn("temperature", bat)
        self.assertIsInstance(bat["percentage"], int)

    def test_volume_info(self):
        vol = device_manager.get_volume_info()
        self.assertIsInstance(vol, dict)
        self.assertIn("music_percent", vol)
        self.assertIn("streams", vol)

    def test_set_volume(self):
        res = device_manager.set_volume(50, "music")
        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("success", False))

    def test_full_device_info(self):
        dev = device_manager.get_full_device_info()
        self.assertIsInstance(dev, dict)
        self.assertIn("battery", dev)
        self.assertIn("volume", dev)
        self.assertIn("api", dev)
        self.assertIn("companion", dev)

    def test_companion_status(self):
        comp = device_manager.get_companion_status()
        self.assertIsInstance(comp, dict)
        self.assertIn("needs_setup", comp)
        self.assertIn("termux_x11", comp)
        self.assertIn("termux_api", comp)
        self.assertIn("ready", comp["termux_x11"])
        self.assertIn("ready", comp["termux_api"])

if __name__ == "__main__":
    unittest.main()
