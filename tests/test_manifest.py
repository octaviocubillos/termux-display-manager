import unittest
import tempfile
from pathlib import Path
from tdm.core.manifest import ManifestLedger

class TestManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_manifest.sqlite3"
        self.ledger = ManifestLedger(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_query_packages(self):
        pkgs = ["tdm_pkg_alpha", "tdm_pkg_beta"]
        self.ledger.record_packages_if_new(pkgs, component="desktop")
        
        installed = self.ledger.get_tdm_installed_packages()
        self.assertEqual(len(installed), 2)
        pkg_names = [p["package_name"] for p in installed]
        self.assertIn("tdm_pkg_alpha", pkg_names)
        self.assertIn("tdm_pkg_beta", pkg_names)

    def test_record_files(self):
        self.ledger.record_file("/tmp/test_file.txt", component="config")
        files = self.ledger.get_tdm_installed_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "/tmp/test_file.txt")

if __name__ == "__main__":
    unittest.main()
