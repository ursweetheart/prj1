"""labelling-queue-feedback: the upload queue (seq-1 steps 2-16). The live API worker only runs the kinds it has
handlers for, so these tests use their own kinds ('test_*') and never race it."""
import shutil

import psycopg
import pytest

import api
from conftest import client
from pipeline import intake
from pipeline.color_extractor import ColorAnalysisResult
from pipeline.processor import SpaceImageProcessor
from pipeline.schemas import FurnitureDetectionResult, SpaceClassificationResult, SpaceSEOMetadata
from pipeline.store import DSN

FOLDER = "zz_test_intake"


class Stub:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def fake_processor(style="Hien_dai", conf=0.62, room_conf=0.8, fail_on=None):
    cls = SpaceClassificationResult(space_type="phong_khach", space_type_confidence=room_conf, design_style=style,
                                    design_style_confidence=conf, style_rationale="x", materials=["gỗ"],
                                    seo_metadata=SpaceSEOMetadata(caption="c", alt_text="a"))
    color = ColorAnalysisResult(palette=[], dominant_hex="#ffffff", brightness="light", temperature="warm", weighted_luminance=70)

    def classify(p, color_res, furniture_res):
        if fail_on and p.name == fail_on:
            raise OSError("cannot identify image file")
        return cls
    proc = object.__new__(SpaceImageProcessor)
    proc.color_engine = lambda p, k=5: color
    proc.detector = Stub(detect=lambda p: FurnitureDetectionResult(objects=[], counts_by_category={}, inference_time_ms=1))
    proc.embedder = Stub(embed_image=lambda p: [0.0] * 768)
    proc.classifier = Stub(classify=classify)
    return proc


@pytest.fixture
def kinds():
    """Register the tests' own task kinds, and clean every trace afterwards."""
    done = []
    intake.HANDLERS["test_ok"] = lambda conn, task, ctx: done.append(task["du_lieu"]["n"])
    intake.HANDLERS["test_fail"] = lambda conn, task, ctx: (_ for _ in ()).throw(ValueError("hỏng"))
    intake.HANDLERS["test_xu_ly_anh"] = intake.process_photo
    yield done
    for k in ("test_ok", "test_fail", "test_xu_ly_anh"):
        intake.HANDLERS.pop(k, None)
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM hang_doi_tac_vu WHERE loai LIKE 'test_%'")
        c.execute("DELETE FROM space WHERE relative_path LIKE %s", (FOLDER + "/%",))
        c.execute("DELETE FROM du_an WHERE slug = %s", (FOLDER.replace("_", "-"),))
    shutil.rmtree(api.IMG_DIR / FOLDER, ignore_errors=True)


def _only_tests(monkeypatch):
    """process_next must only see the tests' kinds, even if real tasks wait in the queue."""
    real = dict(intake.HANDLERS)
    monkeypatch.setattr(intake, "HANDLERS", {k: v for k, v in real.items() if k.startswith("test_")})


def test_tasks_run_in_order_and_a_failure_does_not_stop_the_queue(kinds, monkeypatch):
    _only_tests(monkeypatch)
    with psycopg.connect(DSN, autocommit=True) as c:
        a = intake.enqueue(c, "test_ok", {"n": 1})
        b = intake.enqueue(c, "test_fail", {})
        d = intake.enqueue(c, "test_ok", {"n": 2})
    assert [intake.process_next({}) for _ in range(4)] == [a, b, d, None]
    assert kinds == [1, 2]
    with psycopg.connect(DSN) as c:
        st = dict(c.execute("SELECT id, trang_thai || coalesce(':' || loi, '') FROM hang_doi_tac_vu WHERE id = ANY(%s)",
                            ([a, b, d],)).fetchall())
    assert st == {a: "xong", b: "loi:ValueError: hỏng", d: "xong"}


def test_unknown_kind_is_refused():
    with psycopg.connect(DSN) as c, pytest.raises(ValueError):
        intake.enqueue(c, "khong_co", {})


def test_two_claims_never_take_the_same_task(kinds, monkeypatch):
    _only_tests(monkeypatch)
    with psycopg.connect(DSN, autocommit=True) as c:
        ids = {intake.enqueue(c, "test_ok", {"n": i}) for i in range(2)}
    with psycopg.connect(DSN) as one, psycopg.connect(DSN) as two:  # one holds its claim open while two claims
        first, second = intake.claim(one), intake.claim(two)
        assert {first["id"], second["id"]} == ids


def test_recover_retries_once_then_fails(kinds, monkeypatch):
    _only_tests(monkeypatch)
    with psycopg.connect(DSN, autocommit=True) as c:
        tid = intake.enqueue(c, "test_ok", {"n": 9})
        intake.claim(c)  # running when the "server died"
        intake.recover(c)
        assert c.execute("SELECT trang_thai FROM hang_doi_tac_vu WHERE id=%s", (tid,)).fetchone()[0] == "cho"
        intake.claim(c)  # interrupted a second time
        intake.recover(c)
        assert c.execute("SELECT trang_thai, loi FROM hang_doi_tac_vu WHERE id=%s", (tid,)).fetchone() == \
            ("loi", "bị gián đoạn hai lần")


def test_upload_answers_at_once_then_the_worker_saves_the_ai_proposal(kinds, monkeypatch, as_role):
    monkeypatch.setattr(api, "INGEST_KIND", "test_xu_ly_anh")
    h = as_role("architect")
    files = [("files", ("a.jpg", b"x", "image/jpeg")), ("files", ("b.jpg", b"x", "image/jpeg")),
             ("files", ("c.pdf", b"x", "application/pdf"))]
    r = client.post("/spaces/ingest", files=files, data={"project": FOLDER}, headers=h)
    assert r.status_code == 202
    body = r.json()
    assert [t["trang_thai"] for t in body["tasks"]] == ["dang_xu_ly", "dang_xu_ly"]
    assert body["refused"][0]["name"] == "c.pdf"
    ids = ",".join(str(t["id"]) for t in body["tasks"])

    _only_tests(monkeypatch)
    ctx = {"processor": lambda: fake_processor(fail_on="b.jpg"), "img_dir": api.IMG_DIR}
    while intake.process_next(ctx):
        pass
    st = client.get("/spaces/ingest/tasks", params={"ids": ids}, headers=h).json()
    assert [s["trang_thai"] for s in st] == ["xong", "loi"] and st[0]["space_id"] and "cannot identify" in st[1]["loi"]
    with psycopg.connect(DSN) as c:
        row = c.execute("SELECT space_type_ai, design_style_ai, space_type_confidence, style_confidence, review_status "
                        "FROM space WHERE id = %s", (st[0]["space_id"],)).fetchone()
        logged = c.execute("SELECT user_id IS NOT NULL FROM review_log WHERE space_id=%s AND action='ingest'",
                           (st[0]["space_id"],)).fetchone()
    assert row == ("phong_khach", "Hien_dai", pytest.approx(0.8), pytest.approx(0.62), "draft")
    assert logged == (True,)


def test_upload_limits_and_roles(as_role):
    many = [("files", (f"{i}.jpg", b"x", "image/jpeg")) for i in range(api.MAX_BATCH + 1)]
    assert client.post("/spaces/ingest", files=many, headers=as_role("architect")).status_code == 422
    assert client.get("/spaces/ingest/tasks", params={"ids": "1"}).status_code == 401
    assert client.get("/spaces/ingest/tasks", params={"ids": "1"}, headers=as_role("visitor")).status_code == 403
