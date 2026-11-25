import unittest

from auto_fixer import classify_failure


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

    def test_unknown_error_is_not_misclassified(self):
        self.assertEqual(classify_failure("random build failure"), "unknown")


if __name__ == "__main__":
    unittest.main()
