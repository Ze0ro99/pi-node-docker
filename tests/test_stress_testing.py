import tempfile
import unittest
from pathlib import Path

import yaml

from stress_testing.config import load_config
from stress_testing.engine import Results


class ConfigTests(unittest.TestCase):
    def write_config(self, data):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
        yaml.safe_dump(data, handle)
        handle.close()
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return handle.name

    def valid_config(self):
        return {
            "target": {"base_url": "http://127.0.0.1:8000"},
            "load": {"duration_seconds": 10, "concurrency": 2},
            "endpoints": [{"path": "/health", "method": "GET", "weight": 1}],
        }

    def test_loads_valid_local_config(self):
        config = load_config(self.write_config(self.valid_config()))
        self.assertEqual(config.concurrency, 2)
        self.assertEqual(config.endpoints[0].path, "/health")

    def test_blocks_external_target_by_default(self):
        data = self.valid_config()
        data["target"]["base_url"] = "https://example.com"
        with self.assertRaisesRegex(ValueError, "External targets are blocked"):
            load_config(self.write_config(data))

    def test_rejects_state_changing_method(self):
        data = self.valid_config()
        data["endpoints"][0]["method"] = "POST"
        with self.assertRaisesRegex(ValueError, "Only GET and HEAD"):
            load_config(self.write_config(data))

    def test_rejects_excessive_concurrency(self):
        data = self.valid_config()
        data["load"]["concurrency"] = 501
        with self.assertRaisesRegex(ValueError, "concurrency"):
            load_config(self.write_config(data))


class MetricsTests(unittest.TestCase):
    def test_counts_statuses_errors_and_percentiles(self):
        result = Results()
        result.record(latency_ms=10, status=200)
        result.record(latency_ms=20, status=503)
        result.record(latency_ms=30, error="TimeoutError")
        summary = result.summary(2)
        self.assertEqual(summary["total_requests"], 3)
        self.assertEqual(summary["successful_requests"], 1)
        self.assertEqual(summary["failed_requests"], 2)
        self.assertEqual(summary["status_codes"]["503"], 1)
        self.assertEqual(summary["errors"]["TimeoutError"], 1)
        self.assertEqual(summary["latency_ms"]["average"], 20)


if __name__ == "__main__":
    unittest.main()
