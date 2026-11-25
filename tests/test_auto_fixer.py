import tempfile
import unittest
from pathlib import Path

from auto_fixer import classify_failure, repair_python_source


class AutoFixerTests(unittest.TestCase):
    def test_detects_missing_aidl(self):
        self.assertEqual(
            classify_failure("Aidl not found, please install it."),
            "missing_aidl",
        )

    def test_detects_sdk_license_error(self):
        self.assertEqual(
            classify_failure("Skipping packages because license is not accepted"),
            "sdk_license",
        )

    def test_does_not_claim_to_fix_python_syntax(self):
        self.assertEqual(
            classify_failure("SyntaxError: invalid syntax"),
            "python_source_error",
        )


    def test_removes_accidental_markdown_code_fence_safely(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "main.py"
            source.write_text(f"{chr(96) * 3}python\\nprint(1)\\n{chr(96) * 3}\\n", encoding="utf-8")
            repaired, message = repair_python_source(source)
            self.assertTrue(repaired)
            self.assertEqual(source.read_text(encoding="utf-8"), "print(1)\\n")
            self.assertTrue(source.with_suffix(".py.autofix.bak").exists())

    def test_unknown_error_is_not_misclassified(self):
        self.assertEqual(classify_failure("random build failure"), "unknown")


if __name__ == "__main__":
    unittest.main()
