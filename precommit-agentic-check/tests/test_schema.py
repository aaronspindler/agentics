from __future__ import annotations

import unittest

from agentic_check.schema import SchemaError, parse_model_response


class ParseModelResponseTests(unittest.TestCase):
    def test_valid_payload(self) -> None:
        raw = (
            '{'
            '"status":"pass",'
            '"summary":"looks good",'
            '"findings":[],'
            '"suggested_patch":null'
            '}'
        )

        result = parse_model_response(raw)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["summary"], "looks good")
        self.assertEqual(result["findings"], [])

    def test_fenced_json_payload(self) -> None:
        raw = """```json
{"status":"pass","summary":"ok","findings":[],"suggested_patch":null}
```"""

        result = parse_model_response(raw)

        self.assertEqual(result["status"], "pass")

    def test_fail_requires_findings(self) -> None:
        raw = '{"status":"fail","summary":"bad","findings":[],"suggested_patch":null}'

        with self.assertRaises(SchemaError):
            parse_model_response(raw)


if __name__ == "__main__":
    unittest.main()
