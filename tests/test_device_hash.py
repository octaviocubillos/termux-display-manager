import unittest
import tempfile
import re
from pathlib import Path

from tdm.core.device import (
    DeviceManager,
    get_local_ipv4_addresses,
    get_tailscale_ip,
    format_access_banner,
)
from landing.db import LandingDatabase, HASH_REGEX
from landing.server import DEVICE_ROUTE_REGEX


class TestDeviceHashAndProxy(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.device_db_path = Path(self.temp_dir.name) / "test_device.sqlite3"
        self.landing_db_path = Path(self.temp_dir.name) / "test_landing.sqlite3"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_device_hash_format_and_persistence(self):
        dm = DeviceManager(self.device_db_path)
        h1 = dm.get_or_create_device_hash()

        # Debe tener exactamente 8 letras minúsculas
        self.assertEqual(len(h1), 8)
        self.assertTrue(h1.isalpha())
        self.assertTrue(h1.islower())
        self.assertRegex(h1, r"^[a-z]{8}$")

        # Debe ser estrictamente idempotente
        h2 = dm.get_or_create_device_hash()
        self.assertEqual(h1, h2)

        # Nueva instancia apuntando al mismo SQLite debe recuperar el mismo hash
        dm_reloaded = DeviceManager(self.device_db_path)
        self.assertEqual(dm_reloaded.get_or_create_device_hash(), h1)

    def test_local_ip_excludes_loopback(self):
        ips = get_local_ipv4_addresses()
        for ip in ips:
            self.assertFalse(ip.startswith("127."))
            self.assertNotEqual(ip, "localhost")

    def test_banner_content_https_privacy_and_network_warning(self):
        banner = format_access_banner(port=19050)
        self.assertIn("BENEFICIOS DEL ACCESO CENTRAL HTTPS", banner)
        self.assertIn("PRIVACIDAD TOTAL Y CERO RECOLECCIÓN", banner)
        self.assertIn("CONDICIÓN DE ACCESO CENTRAL", banner)
        self.assertIn("https://tdm.oton.cl/", banner)
        self.assertIn("http://127.0.0.1:19050", banner)
        self.assertIn("Tailscale", banner)

    def test_landing_database_sqlite(self):
        db = LandingDatabase(self.landing_db_path)
        # 1. Registro válido
        reg = db.register_device(
            device_hash="abcdwxyz",
            ips=["192.168.1.50", "127.0.0.1"],
            port=19050,
            tailscale_ip="100.64.0.10"
        )
        self.assertEqual(reg["device_hash"], "abcdwxyz")
        self.assertEqual(reg["ips"], ["192.168.1.50"])  # 127.0.0.1 filtrado
        self.assertEqual(reg["tailscale_ip"], "100.64.0.10")

        # 2. Consulta case-insensitive
        dev = db.get_device("ABCDWXYZ")
        self.assertIsNotNone(dev)
        self.assertEqual(dev["device_hash"], "abcdwxyz")
        self.assertEqual(dev["port"], 19050)

        # 3. Actualización de IP activa
        db.set_last_active_ip("abcdwxyz", "192.168.1.50")
        dev_updated = db.get_device("abcdwxyz")
        self.assertEqual(dev_updated["last_active_ip"], "192.168.1.50")

        # 4. Listado
        dev_list = db.list_devices()
        self.assertEqual(len(dev_list), 1)
        self.assertEqual(dev_list[0]["device_hash"], "abcdwxyz")

        # 5. Validación estricta de hash inválido
        with self.assertRaises(ValueError):
            db.register_device("abc", ["192.168.1.1"])  # Menos de 8 letras
        with self.assertRaises(ValueError):
            db.register_device("abcd1234", ["192.168.1.1"])  # Contiene números

    def test_dynamic_route_regex(self):
        m1 = DEVICE_ROUTE_REGEX.match("/abcdwxyz")
        self.assertIsNotNone(m1)
        self.assertEqual(m1.group(1), "abcdwxyz")
        self.assertIsNone(m1.group(2))

        m2 = DEVICE_ROUTE_REGEX.match("/abcdwxyz/")
        self.assertIsNotNone(m2)
        self.assertEqual(m2.group(1), "abcdwxyz")
        self.assertEqual(m2.group(2), "")

        m3 = DEVICE_ROUTE_REGEX.match("/abcdwxyz/api/status")
        self.assertIsNotNone(m3)
        self.assertEqual(m3.group(1), "abcdwxyz")
        self.assertEqual(m3.group(2), "api/status")

        # No debe coincidir con rutas estáticas normales
        self.assertIsNone(DEVICE_ROUTE_REGEX.match("/install"))
        self.assertIsNone(DEVICE_ROUTE_REGEX.match("/clean"))
        self.assertIsNone(DEVICE_ROUTE_REGEX.match("/aabbcc"))  # 6 letras


if __name__ == "__main__":
    unittest.main()
