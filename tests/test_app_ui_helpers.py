from app import _has_test_error, _language_for_file


def test_language_for_file_uses_known_extension_and_text_fallback():
    assert _language_for_file("src/main.py") == "python"
    assert _language_for_file("README") == "text"


def test_has_test_error_detects_runtime_failure_markers():
    assert _has_test_error("Traceback\nModuleNotFoundError: missing package") is True
    assert _has_test_error("All tests passed") is False
