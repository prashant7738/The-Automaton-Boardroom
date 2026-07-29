"""Unit tests for agency.nodes._detect_project_type.

Regression coverage for a bug where a frontend-only React project whose files
were nested under "frontend/" (with no matching "backend/") was misdetected as
a plain React project but its files kept the "frontend/" prefix. Since
`_run_react` runs `npm install`/`npm run build` at the sandbox root, this
caused: `npm ERR! enoent ... open '/home/user/package.json'`.
"""

from agency.nodes import _detect_project_type


class TestDetectProjectType:
    def test_root_package_json_is_react_and_unmodified(self):
        source_files = {"package.json": "{}", "src/App.jsx": "export default () => null;"}
        result = _detect_project_type(source_files)
        assert result["is_react"] is True
        assert result["is_fullstack"] is False
        assert result["source_files"] == source_files

    def test_frontend_only_package_json_is_flattened(self):
        source_files = {
            "frontend/package.json": "{}",
            "frontend/src/App.jsx": "export default () => null;",
        }
        result = _detect_project_type(source_files)
        assert result["is_react"] is True
        assert result["is_fullstack"] is False
        assert result["source_files"] == {
            "package.json": "{}",
            "src/App.jsx": "export default () => null;",
        }

    def test_fullstack_frontend_and_backend_is_not_flattened(self):
        source_files = {
            "frontend/package.json": "{}",
            "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()",
        }
        result = _detect_project_type(source_files)
        assert result["is_fullstack"] is True
        # fullstack layout must keep its "frontend/"/"backend/" prefixes intact
        assert result["source_files"] == source_files

    def test_django_project_detected(self):
        source_files = {"manage.py": "...", "app/views.py": "django code"}
        result = _detect_project_type(source_files)
        assert result["is_django"] is True
        assert result["is_react"] is False

    def test_fastapi_project_detected(self):
        source_files = {"main.py": "from fastapi import FastAPI\napp = FastAPI()"}
        result = _detect_project_type(source_files)
        assert result["is_fastapi"] is True
        assert result["is_react"] is False
