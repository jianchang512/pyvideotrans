"""
Unit tests for pyVideoTrans i18n translation integrity.
Uses standard library unittest (no external dependencies required).
"""
import unittest
from tools.check_i18n import (
    extract_code_tr_keys,
    load_language_files,
    check_cjk_in_keys,
    check_missing_keys,
    check_placeholder_mismatches,
    ROOT_DIR,
)


class TestI18nIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lang_data = load_language_files()
        cls.code_keys = extract_code_tr_keys(ROOT_DIR)

    def test_no_cjk_in_translation_keys(self):
        """Ensure all translation keys across all JSON files are English only (no Chinese keys)."""
        cjk_errors = check_cjk_in_keys(self.lang_data)
        self.assertEqual(cjk_errors, [], f"Found non-English/CJK keys in translation files: {cjk_errors[:5]}")

    def test_all_code_keys_exist_in_zh_cn_json(self):
        """Ensure every tr('...') key in Python code has a corresponding translation in zh-CN.json."""
        missing = check_missing_keys(self.code_keys, self.lang_data)
        self.assertEqual(missing.get("zh-CN", []), [], f"zh-CN.json is missing keys used in code: {missing.get('zh-CN', [])[:5]}")

    def test_all_code_keys_exist_in_en_json(self):
        """Ensure every tr('...') key in Python code exists in en.json."""
        missing = check_missing_keys(self.code_keys, self.lang_data)
        self.assertEqual(missing.get("en", []), [], f"en.json is missing keys used in code: {missing.get('en', [])[:5]}")

    def test_placeholder_consistency(self):
        """Ensure placeholder {} count matches between source and translated values."""
        mismatches = check_placeholder_mismatches(self.lang_data)
        self.assertEqual(mismatches, [], f"Placeholder count mismatches found: {mismatches[:5]}")


if __name__ == "__main__":
    unittest.main()
