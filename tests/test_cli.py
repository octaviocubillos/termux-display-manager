import unittest
import subprocess
import sys

class TestCLI(unittest.TestCase):
    def test_cli_help(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Termux Display Manager CLI", res.stdout)
        self.assertIn("status", res.stdout)
        self.assertIn("doctor", res.stdout)
        self.assertIn("start", res.stdout)
        self.assertIn("stop", res.stdout)
        self.assertIn("server", res.stdout)
        self.assertIn("hub", res.stdout)
        self.assertIn("agent", res.stdout)

    def test_cli_version(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Termux Display Manager (TDM) v", res.stdout)

if __name__ == "__main__":
    unittest.main()
