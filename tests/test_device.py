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

if __name__ == "__main__":
    unittest.main()
