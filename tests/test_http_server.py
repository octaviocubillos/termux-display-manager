import unittest
import asyncio
from tdm.server.http_server import AsyncHTTPServer
from tdm.constants import PORT_TDM_SERVER

class TestHTTPServer(unittest.TestCase):
    def test_server_init(self):
        server = AsyncHTTPServer(host="127.0.0.1", port=19050)
        self.assertEqual(server.port, 19050)
        self.assertEqual(server.host, "127.0.0.1")
        self.assertFalse(server.is_hub)

    def test_hub_init(self):
        hub = AsyncHTTPServer(host="0.0.0.0", port=19050, is_hub=True)
        self.assertTrue(hub.is_hub)

if __name__ == "__main__":
    unittest.main()
