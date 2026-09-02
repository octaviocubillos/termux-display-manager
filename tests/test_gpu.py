import unittest
from tdm.core.gpu_manager import gpu_manager

class TestGPUManager(unittest.TestCase):
    def test_get_gpu_info(self):
        info = gpu_manager.get_gpu_info()
        self.assertIsInstance(info, dict)
        self.assertIn("gpu_model", info)
        self.assertIn("gpu_vendor", info)
        self.assertIn("driver_type", info)
        self.assertIn("virgl_supported", info)

    def test_is_3d_installed_boolean(self):
        res = gpu_manager.is_3d_installed()
        self.assertIsInstance(res, bool)

if __name__ == "__main__":
    unittest.main()
