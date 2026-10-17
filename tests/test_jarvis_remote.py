import json
import socket
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from jarvis_remote import JarvisRemoteServer


class JarvisRemoteTests(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.remote = JarvisRemoteServer(
            lambda command: self.commands.append(command) or "accepted",
            lambda: {"cpu": 10, "host": "test"},
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.token = self.remote.start(port=port)
        self.port = self.remote.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.remote.stop()

    def request(self, path, method="GET", token=None, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.loads(response.read().decode())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def test_requires_token(self):
        status, _ = self.request("/api/status")
        self.assertEqual(status, 401)

    def test_status_with_token(self):
        status, payload = self.request("/api/status", token=self.token)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])

    def test_rejects_arbitrary_shell(self):
        status, payload = self.request(
            "/api/command", "POST", self.token, {"command": "run whoami"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.commands, [])

    def test_launch_is_forwarded_to_allowlisted_handler(self):
        status, payload = self.request(
            "/api/command", "POST", self.token, {"command": "launch notepad"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.commands, ["launch notepad"])


if __name__ == "__main__":
    unittest.main()
