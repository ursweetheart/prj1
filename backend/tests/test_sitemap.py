"""sitemap.xml (change topic-guard-sitemap-item-services; seq-6 b18). Throw-away spaces 'test_sm_*', removed afterwards."""
import uuid
import xml.etree.ElementTree as ET

import psycopg
import pytest

from conftest import client
from pipeline.store import DSN

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@pytest.fixture
def folder():
    f = f"test_sm_{uuid.uuid4().hex[:6]}"
    made = []

    def add(status):
        with psycopg.connect(DSN) as c:
            sid = c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status) VALUES "
                            "(%s, 'phong_khach', 'Japandi', %s) RETURNING id", (f"{f}/{uuid.uuid4().hex[:4]}.jpg", status)).fetchone()[0]
        made.append(sid)
        return sid
    yield f, add
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space WHERE id = ANY(%s)", (made,))


def _read():
    r = client.get("/sitemap.xml")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/xml")
    root = ET.fromstring(r.content)
    return {u.find("s:loc", NS).text: (u.find("s:lastmod", NS).text if u.find("s:lastmod", NS) is not None else None)
            for u in root.findall("s:url", NS)}


def test_lists_published_only_and_follows_takedown(folder, as_role, monkeypatch):
    monkeypatch.setenv("D3_FRONTEND_URL", "https://d3studio.example/")
    f, add = folder
    pub, draft, internal = add("published"), add("draft"), add("noi_bo")
    urls = _read()
    site = "https://d3studio.example/"
    assert all(u.startswith(site) for u in urls)
    assert site in urls and site + "ve-chung-toi" in urls
    project = site + "du-an/" + f.replace("_", "-")
    assert urls[site + f"khong-gian/{pub}"] and urls[project]
    assert site + f"khong-gian/{draft}" not in urls and site + f"khong-gian/{internal}" not in urls
    assert not any(p in u for u in urls for p in ("/quan-tri", "/khach-hang", "/dang-nhap", "/dat-mat-khau",
                                                   "/quen-mat-khau", "/bo-suu-tap"))

    r = client.post("/spaces/unpublish", json={"space_ids": [pub], "ly_do": "Nhãn sai cần sửa lại", "giu_noi_bo": False},
                    headers=as_role("lead_architect"))
    assert r.status_code == 200, r.text
    urls = _read()
    assert site + f"khong-gian/{pub}" not in urls and project not in urls  # its only published photo is gone


def test_project_without_published_photo_absent(folder):
    f, add = folder
    add("draft")
    assert not any(f.replace("_", "-") in u for u in _read())
