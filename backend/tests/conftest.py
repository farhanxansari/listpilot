"""Test settings: no real API key, a throwaway database and upload folder."""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="listpilot_test_")
os.environ["LLM_BASE_URL"] = "http://test.invalid"
os.environ["LLM_API_KEY"] = "test"
os.environ["LLM_MODEL"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
