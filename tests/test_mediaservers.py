"""Plex/Jellyfin mot en påhittad server – testerna går aldrig ut på nätet."""
import asyncio

import httpx

from app import mediaservers, settings


def test_jellyfin_uses_authorization_header(config_dir, monkeypatch):
    seen = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers.get("authorization", "")
        if 'Token="nyckel123"' not in seen["auth"] or "x-emby-token" in request.headers:
            return httpx.Response(401)  # som Jellyfin 12 med det gamla sättet avstängt
        return httpx.Response(200, json={"Items": [
            {"Type": "Movie", "Name": "Alien", "ProductionYear": 1979, "ProviderIds": {"Imdb": "tt0078748", "Tmdb": "348"}},
            {"Type": "Series", "Name": "24", "ProviderIds": {"Tvdb": "76290"}}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(settings, "get", lambda key: {"jellyfin_url": "http://192.168.1.243:8096",
                                                      "jellyfin_api_key": "nyckel123"}.get(key, ""))
    items = asyncio.run(mediaservers.fetch_jellyfin())
    assert seen["auth"].startswith("MediaBrowser ")
    assert items == [{"kind": "movie", "imdb_id": "tt0078748", "tmdb_id": 348, "title": "Alien", "year": 1979},
                     {"kind": "tv", "imdb_id": None, "tmdb_id": None, "title": "24", "year": None}]
