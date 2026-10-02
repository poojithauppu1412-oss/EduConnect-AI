import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class HealthEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_liveness_reports_api_process(self) -> None:
        response = self.client.get("/api/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_api_root_returns_service_information(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "EduConnect AI")

    def test_readiness_checks_postgresql(self) -> None:
        response = self.client.get("/api/health/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})


if __name__ == "__main__":
    unittest.main()