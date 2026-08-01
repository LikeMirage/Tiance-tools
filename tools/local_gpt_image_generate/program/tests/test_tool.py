from __future__ import annotations

import base64
import os
from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_DIR))

from errors import ToolError
from image_output import detect_format, save_image
from image_api_client import build_request_payload, extract_image_base64, redact_secret
from settings import parse_options, validate_size


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image"


class ToolContractTests(unittest.TestCase):
    def test_request_uses_image_generation_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with temporary_workspace(directory):
                options = parse_options({"prompt": "画一只猫"})
                payload = build_request_payload(options)
        self.assertEqual(payload["model"], "gpt-image-2")
        self.assertEqual(payload["prompt"], "画一只猫")
        self.assertEqual(payload["n"], 1)

    def test_extracts_image_api_base64_result(self) -> None:
        encoded = base64.b64encode(PNG_BYTES).decode("ascii")
        result = extract_image_base64({"data": [{"b64_json": encoded}]})
        self.assertEqual(result, encoded)

    def test_output_path_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with temporary_workspace(directory):
                with self.assertRaises(ToolError) as raised:
                    parse_options({"prompt": "test", "output_path": "../escape.png"})
        self.assertEqual(raised.exception.code, "OUTPUT_OUTSIDE_WORKSPACE")

    def test_size_constraints_are_validated(self) -> None:
        self.assertEqual(validate_size("1536x1024"), "1536x1024")
        with self.assertRaises(ToolError):
            validate_size("1000x1000")

    def test_image_is_saved_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with temporary_workspace(directory):
                options = parse_options({"prompt": "test", "output_path": "generated/test.png"})
                metadata, warnings = save_image(PNG_BYTES, options)
                self.assertEqual(metadata["output_path"], "generated/test.png")
                self.assertEqual(warnings, [])
                self.assertTrue((Path(directory) / "generated/test.png").exists())

    def test_detect_format_rejects_unknown_bytes(self) -> None:
        with self.assertRaises(ToolError):
            detect_format(b"not-an-image")

    def test_upstream_error_redacts_api_key(self) -> None:
        self.assertEqual(redact_secret("invalid secret-value", "secret-value"), "invalid [REDACTED]")


class temporary_workspace:
    def __init__(self, path: str) -> None:
        self.path = path
        self.previous = os.environ.get("TIANCE_WORKSPACE_ROOT")

    def __enter__(self) -> None:
        os.environ["TIANCE_WORKSPACE_ROOT"] = self.path

    def __exit__(self, *_: object) -> None:
        if self.previous is None:
            os.environ.pop("TIANCE_WORKSPACE_ROOT", None)
        else:
            os.environ["TIANCE_WORKSPACE_ROOT"] = self.previous


if __name__ == "__main__":
    unittest.main()
