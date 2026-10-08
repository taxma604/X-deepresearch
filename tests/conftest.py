import pytest


@pytest.fixture(autouse=True)
def isolated_local_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("X_DEEPRESEARCH_CONFIG_DIR", str(tmp_path / "config"))
