"""Gemensamt för testerna: varje test får en egen tom appdata-mapp."""
import os
import sys
import tempfile

# CONFIG_DIR läses när modulerna importeras, så den måste sättas innan app importeras
os.environ.setdefault("CONFIG_DIR", tempfile.mkdtemp(prefix="diskoteket-test-"))
os.environ["LOOKUP_MUSICBRAINZ"] = "0"  # testerna ska aldrig gå ut på nätet
os.environ["LOOKUP_UPCITEMDB"] = "0"
os.environ["LOOKUP_MYMOVIES"] = "0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from app import auth, db, posters, repo, settings  # noqa: E402


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "diskoteket.db"))
    monkeypatch.setattr(db, "LEGACY_DB", str(tmp_path / "samling.db"))
    monkeypatch.setattr(repo, "BACKUP_DIR", str(tmp_path / "backup"))
    monkeypatch.setattr(posters, "POSTER_DIR", str(tmp_path / "posters"))
    monkeypatch.setattr(auth, "AUTH_PATH", str(tmp_path / "auth.json"))
    settings._cache = None
    auth._data = None
    yield tmp_path
    settings._cache = None
    auth._data = None
