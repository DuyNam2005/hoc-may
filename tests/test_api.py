import json
import math
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8000"

SAMPLE = {
    "forecast_date": "2011-01-01",
    "hr": 0,
    "season": 1,
    "holiday": 0,
    "weathersit": 1,
    "temp": 0.24,
    "atemp": 0.2879,
    "hum": 0.81,
    "windspeed": 0.0,
}


def call_api(path, payload=None):
    body = None
    headers = {}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(
                response.read().decode("utf-8")
            )
    except HTTPError as error:
        return error.code, json.loads(
            error.read().decode("utf-8")
        )


class TestBikeDemandAPI(unittest.TestCase):
    def test_health(self):
        status, data = call_api("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    def test_valid_forecast(self):
        status, data = call_api("/api/forecast", SAMPLE)
        self.assertEqual(status, 200)

        self.assertTrue(math.isfinite(data["prediction"]))
        self.assertGreaterEqual(data["prediction"], 0)
        self.assertEqual(
            data["prediction"],
            max(data["raw_prediction"], 0),
        )
        self.assertEqual(data["forecast_date"], "2011-01-01")
        self.assertEqual(data["hour"], 0)
        self.assertEqual(data["unit"], "lượt thuê/giờ")
        self.assertIsInstance(data["warnings"], list)

    def test_missing_temperature(self):
        payload = SAMPLE.copy()
        del payload["temp"]

        status, data = call_api("/api/forecast", payload)
        self.assertEqual(status, 422)
        self.assertIn("detail", data)

        # Sau request lỗi, request hợp lệ vẫn phải chạy được.
        status, _ = call_api("/api/forecast", SAMPLE)
        self.assertEqual(status, 200)

    def test_invalid_values(self):
        invalid_cases = [
            ("hr", 24),
            ("hr", -1),
            ("hr", 1.5),
            ("temp", 1.1),
            ("hum", -0.1),
            ("weathersit", 5),
            ("forecast_date", "2026-01-01"),
            ("forecast_date", "2011-02-30"),
        ]

        for field, value in invalid_cases:
            with self.subTest(field=field, value=value):
                payload = {**SAMPLE, field: value}
                status, data = call_api("/api/forecast", payload)
                self.assertEqual(status, 422)
                self.assertIn("detail", data)

    def test_reject_target_fields(self):
        for field in ["cnt", "casual", "registered"]:
            with self.subTest(field=field):
                payload = {**SAMPLE, field: 100}
                status, _ = call_api("/api/forecast", payload)
                self.assertEqual(status, 422)

    def test_calendar_features(self):
        # 03/01/2011 là thứ Hai, không phải ngày lễ.
        payload = {
            **SAMPLE,
            "forecast_date": "2011-01-03",
            "holiday": 0,
        }
        status, data = call_api("/api/forecast", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["features_used"]["weekday"], 1)
        self.assertEqual(data["features_used"]["workingday"], 1)

        # Cùng ngày nhưng kịch bản là ngày lễ.
        payload["holiday"] = 1
        status, data = call_api("/api/forecast", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["features_used"]["workingday"], 0)

    def test_report_endpoints(self):
        for path in [
            "/api/evaluation",
            "/api/model-card",
            "/api/experiments",
        ]:
            with self.subTest(path=path):
                status, data = call_api(path)
                self.assertEqual(status, 200)
                self.assertIsInstance(data, dict)
                self.assertTrue(data)


if __name__ == "__main__":
    unittest.main()