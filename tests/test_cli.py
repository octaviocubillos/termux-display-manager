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

    def test_cli_novnc_help(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "novnc", "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("novnc", res.stdout.lower())
        self.assertIn("start", res.stdout)
        self.assertIn("status", res.stdout)
        self.assertIn("url", res.stdout)

    def test_cli_novnc_status(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "novnc", "status"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("TDM noVNC", res.stdout)

    def test_cli_novnc_url(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "novnc", "url"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("http://", res.stdout)
        self.assertIn("/novnc/vnc.html", res.stdout)

    def test_cli_scale(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "scale", "1"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("TDM Scale", res.stdout)

    def test_cli_status_json(self):
        res = subprocess.run([sys.executable, "-m", "tdm.cli.main", "status", "--json"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("installed_desktop", res.stdout)

    def test_execute_cli_command(self):
        import asyncio
        from tdm.cli.main import execute_cli_command
        res = asyncio.run(execute_cli_command(["status"]))
        self.assertTrue(res.get("success"))
        self.assertIn("installed_desktop", res.get("data", {}))

if __name__ == "__main__":
    unittest.main()
