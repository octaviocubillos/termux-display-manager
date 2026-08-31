import unittest
from tdm.discovery.desktops import discover_desktops, get_desktop_by_id
from tdm.discovery.backends import discover_backends, get_backend_by_id
from tdm.discovery.network import discover_network_interfaces

class TestDiscovery(unittest.TestCase):
    def test_discover_desktops(self):
        desktops = discover_desktops()
        self.assertIsInstance(desktops, list)
        self.assertGreater(len(desktops), 0)
        ids = [d["id"] for d in desktops]
        self.assertIn("xfce4", ids)
        self.assertIn("kde", ids)
        self.assertIn("mate", ids)

    def test_get_desktop_by_id(self):
        d1 = get_desktop_by_id("xfce4")
        self.assertIsNotNone(d1)
        self.assertEqual(d1["name"], "XFCE4")

        # Alias test
        d2 = get_desktop_by_id("xfce")
        self.assertIsNotNone(d2)
        self.assertEqual(d2["name"], "XFCE4")

    def test_discover_backends(self):
        backends = discover_backends()
        self.assertIsInstance(backends, list)
        ids = [b["id"] for b in backends]
        self.assertIn("termux-x11", ids)
        self.assertIn("novnc", ids)
        self.assertIn("vnc", ids)
        self.assertIn("rdp", ids)

    def test_network_interfaces(self):
        net = discover_network_interfaces(port=19050)
        self.assertIn("ports", net)
        self.assertEqual(net["ports"]["pwa_server"], 19050)
        self.assertIn("access_urls", net)
        self.assertIn("local", net["access_urls"])

if __name__ == "__main__":
    unittest.main()
