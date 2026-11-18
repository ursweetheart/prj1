"""Proposed hotspots (change: hotspot-accuracy 2.1). No GPU, no AI: detections and items are built by hand."""

from pipeline.hotspots import propose
from pipeline.schemas import AiItem, BoundingBox, DetectedFurniture


def box(label, conf, x0, y0, x1, y1):
    return DetectedFurniture(label=label, label_vi=label, confidence=conf, bbox=BoundingBox(x_min=x0, y_min=y0, x_max=x1, y_max=y1),
                             hotspot_anchor=((x0 + x1) / 2, (y0 + y1) / 2))


def item(ten, loai, x, y):
    return AiItem(ten=ten, loai=loai, x=x, y=y)


SOFA = box("couch", 0.9, 0.1, 0.5, 0.7, 0.9)


def test_items_the_detector_cannot_see_become_points_without_a_box():
    out = propose([], [item("Đèn chùm pha lê", "den", 0.5, 0.1), item("Thảm len kem", "thao", 0.4, 0.85)])
    assert [(o.label_vi, o.label, o.bbox, o.nguon_ai) for o in out] == [
        ("Đèn chùm pha lê", "den", None, "gemini"), ("Thảm len kem", "thao", None, "gemini")]


def test_ai_point_replaces_the_box_centre():
    out = propose([SOFA], [item("Sofa chữ L xám", "sofa", 0.2, 0.75)])
    assert len(out) == 1
    o = out[0]
    assert (o.label_vi, o.label, o.hotspot_anchor, o.confidence, o.nguon_ai) == ("Sofa chữ L xám", "couch", (0.2, 0.75), 0.9, "ca_hai")
    assert o.bbox == SOFA.bbox


def test_a_lamp_point_inside_a_sofa_box_does_not_merge():
    out = propose([SOFA], [item("Đèn cây", "den", 0.3, 0.6)])
    assert [(o.label, o.nguon_ai) for o in out] == [("den", "gemini"), ("couch", "yolo")]


def test_unmatched_weak_chair_is_dropped():
    assert propose([box("chair", 0.45, 0.1, 0.1, 0.2, 0.3)], []) == []


def test_overlapping_couches_become_one_and_clutter_goes():
    dup = box("couch", 0.6, 0.12, 0.52, 0.68, 0.88)
    clutter = [box("bottle", 0.9, 0.5, 0.5, 0.52, 0.55)] + [box("cup", 0.8, 0.6, 0.6, 0.62, 0.62)] * 3
    out = propose([SOFA, dup, *clutter], [])
    assert [(o.label, o.confidence) for o in out] == [("couch", 0.9)]


def test_low_confidence_boxes_are_dropped():
    assert propose([box("bed", 0.35, 0.1, 0.1, 0.9, 0.9)], []) == []


def test_cap_and_order_merged_then_ai_only_then_detector_only():
    beds = [box("bed", 0.9, 0.0, 0.5, 0.5, 1.0), box("chair", 0.8, 0.6, 0.6, 0.7, 0.8),
            box("tv", 0.7, 0.8, 0.1, 0.95, 0.3), box("dining table", 0.85, 0.55, 0.1, 0.75, 0.3)]
    items = [item("Ghế gỗ", "ghe", 0.65, 0.7), item("Giường", "giuong", 0.2, 0.8)] + [
        item(f"Tranh {i}", "tranh", 0.1 * i, 0.05) for i in range(1, 6)]
    out = propose(beds, items)
    assert len(out) == 6
    assert [o.nguon_ai for o in out] == ["ca_hai", "ca_hai", "gemini", "gemini", "gemini", "gemini"]
    assert [o.label_vi for o in out[:2]] == ["Giường", "Ghế gỗ"]  # larger box first


def test_without_ai_items_the_detector_alone_keeps_one_point_per_kind():
    many = [box("chair", 0.9, 0.1 * i, 0.1, 0.1 * i + 0.05, 0.2) for i in range(9)] + [SOFA]
    out = propose(many, [])
    assert sorted(o.label for o in out) == ["chair", "couch"] and all(o.nguon_ai == "yolo" for o in out)


def test_identical_items_get_one_point_different_ones_keep_theirs():
    chairs = [item("Ghế ăn bọc vải kem", "ghe", 0.2 + 0.1 * i, 0.7) for i in range(4)]
    out = propose([box("chair", 0.9, 0.85, 0.6, 0.95, 0.9)],  # a detector chair: the AI already named the chairs
                  chairs + [item("ghế ăn  bọc vải KEM", "ghe", 0.6, 0.7), item("Ghế thư giãn cam", "ghe", 0.9, 0.5)])
    assert [o.label_vi for o in out] == ["Ghế ăn bọc vải kem", "Ghế thư giãn cam"]


def test_a_box_serves_one_item():
    out = propose([SOFA], [item("Sofa", "sofa", 0.2, 0.7), item("Sofa 2", "sofa", 0.5, 0.7)])
    assert [o.nguon_ai for o in out] == ["ca_hai", "gemini"]


# ── 2.2: the upload pipeline saves the proposed hotspots ─────────────────────────────────────────────────────────
def test_processed_photo_saves_proposed_hotspots(tmp_path):
    import psycopg

    from pipeline.assistant import with_services
    from pipeline.color_extractor import ColorAnalysisResult
    from pipeline.processor import SpaceImageProcessor
    from pipeline.schemas import FurnitureDetectionResult, SpaceClassificationResult, SpaceSEOMetadata
    from pipeline.store import DSN, save_records

    class Stub:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    detected = FurnitureDetectionResult(objects=[SOFA, box("couch", 0.6, 0.12, 0.52, 0.68, 0.88), box("bottle", 0.9, 0.5, 0.5, 0.52, 0.55),
                                                 box("chair", 0.45, 0.8, 0.6, 0.9, 0.8)],
                                        counts_by_category={"couch": 2, "bottle": 1, "chair": 1}, inference_time_ms=1)
    cls = SpaceClassificationResult(space_type="phong_khach", design_style="Hien_dai", design_style_confidence=0.9, style_rationale="x",
                                    materials=["gỗ"], seo_metadata=SpaceSEOMetadata(caption="c", alt_text="a"),
                                    items=[item("Sofa chữ L", "sofa", 0.2, 0.75), item("Đèn chùm", "den", 0.5, 0.1)])
    color = ColorAnalysisResult(palette=[], dominant_hex="#ffffff", brightness="light", temperature="warm", weighted_luminance=70)
    proc = object.__new__(SpaceImageProcessor)
    proc.color_engine = lambda p, k=5: color
    proc.detector = Stub(detect=lambda p: detected)
    proc.embedder = Stub(embed_image=lambda p: [0.0] * 768)
    proc.classifier = Stub(classify=lambda p, color_res, furniture_res: cls)
    img = tmp_path / "test_hsa_p" / "anh.jpg"
    img.parent.mkdir()
    img.write_bytes(b"x")
    rec = proc.process_image(img, base_dir=tmp_path)
    assert rec.furniture_detection.counts_by_category == {"couch": 2, "bottle": 1, "chair": 1}  # raw evidence kept
    try:
        save_records([rec])
        with psycopg.connect(DSN) as c:
            hs = c.execute("SELECT hotspots FROM space WHERE relative_path = 'test_hsa_p/anh.jpg'").fetchone()[0]
        objs = hs["objects"]
        assert len(objs) <= 6 and [(o["label_vi"], o["nguon_ai"]) for o in objs] == [("Sofa chữ L", "ca_hai"), ("Đèn chùm", "gemini")]
        assert all(o.get("nguon_tao", "ai") == "ai" for o in objs)
        assert with_services(hs)["objects"][0]["service"]  # the sofa still maps to a service through its label
        with psycopg.connect(DSN) as c:  # project-catalog 2.4: a photo in a new folder joins that folder's project
            assert c.execute("SELECT s.du_an_slug, d.ten, d.co_trang FROM space s JOIN du_an d ON d.slug = s.du_an_slug "
                             "WHERE relative_path = 'test_hsa_p/anh.jpg'").fetchone() == ("test-hsa-p", "test_hsa_p", False)
    finally:
        with psycopg.connect(DSN) as c:
            c.execute("DELETE FROM space WHERE relative_path = 'test_hsa_p/anh.jpg'")
            c.execute("DELETE FROM du_an WHERE slug = 'test-hsa-p'")
