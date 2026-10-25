"""TMDB-funktionerna i 4.1 (trailer, streaming, liknande, personer, säsonger, släppdatum)
mot påhittade svar i samma format som TMDB – testerna går aldrig ut på nätet."""
import asyncio

import httpx
import pytest

from app import settings, tmdb

RESPONSES = {
    "/movie/348/videos": {"results": [
        {"site": "YouTube", "type": "Teaser", "key": "teaser1", "official": True, "size": 1080, "name": "Teaser"},
        {"site": "YouTube", "type": "Trailer", "key": "trailer1", "official": True, "size": 1080, "name": "Alien – Trailer"},
        {"site": "Vimeo", "type": "Trailer", "key": "x"}]},
    "/movie/348/watch/providers": {"results": {"SE": {
        "link": "https://www.themoviedb.org/movie/348/watch?locale=SE",
        "flatrate": [{"provider_name": "Disney Plus", "logo_path": "/d.jpg", "display_priority": 2},
                     {"provider_name": "Netflix", "logo_path": "/n.jpg", "display_priority": 1}],
        "rent": [{"provider_name": "SF Anytime", "logo_path": "/sf.jpg", "display_priority": 5}]}}},
    "/movie/348/recommendations": {"results": [{"id": 679, "title": "Aliens", "release_date": "1986-07-18", "poster_path": "/a.jpg"}]},
    "/movie/348/similar": {"results": [{"id": 679, "title": "Aliens", "release_date": "1986-07-18"},
                                       {"id": 8077, "title": "Alien³", "release_date": "1992-05-22"}]},
    "/search/person": {"results": [{"id": 10205, "name": "Sigourney Weaver", "known_for_department": "Acting"}]},
    "/person/10205/combined_credits": {
        "cast": [{"id": 348, "media_type": "movie", "title": "Alien", "release_date": "1979-05-25", "character": "Ripley"},
                 {"id": 1, "media_type": "tv", "name": "Talkshow", "first_air_date": "2001-01-01", "character": "Self"}],
        "crew": [{"id": 999, "media_type": "movie", "title": "Egen film", "release_date": "2030-01-01", "job": "Director"}]},
    "/tv/1973/": {"seasons": [{"season_number": 0, "name": "Specials"},
                              {"season_number": 1, "name": "Säsong 1", "episode_count": 24, "air_date": "2001-11-06"},
                              {"season_number": 2, "name": "Säsong 2", "episode_count": 24, "air_date": "2099-10-29"}]},
    "/movie/348/release_dates": {"results": [
        {"iso_3166_1": "US", "release_dates": [{"type": 5, "release_date": "1999-10-26T00:00:00.000Z"}]},
        {"iso_3166_1": "SE", "release_dates": [{"type": 3, "release_date": "1979-09-10T00:00:00.000Z"},
                                               {"type": 5, "release_date": "2003-12-03T00:00:00.000Z"}]}]},
}


@pytest.fixture
def fake_tmdb(config_dir, monkeypatch):
    def handler(request: httpx.Request):
        path = request.url.path.removeprefix("/3")
        data = RESPONSES.get(path) or RESPONSES.get(path + "/")
        return httpx.Response(200, json=data) if data is not None else httpx.Response(404, json={})
    monkeypatch.setattr(settings, "get", lambda key: "token" if key == "tmdb_token" else "sv-SE" if key == "tmdb_language" else "")
    monkeypatch.setattr(tmdb, "_client", httpx.AsyncClient(base_url="https://api.themoviedb.org/3",
                                                           transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(tmdb, "_client_token", "token")


def run(coro):
    return asyncio.run(coro)


def test_trailer_prefers_official_trailer(fake_tmdb):
    assert run(tmdb.trailer(348, "movie")) == {"key": "trailer1", "name": "Alien – Trailer"}


def test_watch_providers_sweden(fake_tmdb):
    p = run(tmdb.watch_providers(348, "movie"))
    assert [x["name"] for x in p["stream"]] == ["Netflix", "Disney Plus"]
    assert [x["name"] for x in p["rent"]] == ["SF Anytime"] and p["buy"] == []


def test_recommendations_fill_up_with_similar(fake_tmdb):
    recs = run(tmdb.recommendations(348, "movie"))
    assert [(r["title"], r["year"]) for r in recs] == [("Aliens", 1986), ("Alien³", 1992)]


def test_person_skips_talkshows(fake_tmdb):
    p = run(tmdb.person("sigourney weaver"))
    assert p["name"] == "Sigourney Weaver"
    assert [(w["title"], w["role"]) for w in p["works"]] == [("Egen film", "Regi"), ("Alien", "Ripley")]


def test_tv_seasons_without_specials(fake_tmdb):
    s = run(tmdb.tv_seasons(1973))
    assert [(x["season"], x["episodes"], x["aired"]) for x in s] == [(1, 24, True), (2, 24, False)]


def test_physical_release_prefers_sweden(fake_tmdb):
    assert run(tmdb.physical_release(348)) == "2003-12-03"
