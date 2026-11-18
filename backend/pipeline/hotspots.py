"""Proposed hotspots for a photo: the detector's boxes merged with the items the classifier named and pointed at,
cleaned and capped (change: hotspot-accuracy).

YOLO (COCO) gives boxes and confidences but knows no lamp, rug, cabinet, curtain, mirror or artwork, and its box centre
often lies in empty space. Gemini, in the classification call it already makes, names the main items and points at
each one. One pure function decides the final list, so it is testable without a GPU or the AI.
"""

# Gemini's item categories -> the detector label used for the same thing (with_services maps services by label);
# categories COCO doesn't have keep their own name as the label.
CATEGORY_LABEL = {
    "sofa": "couch", "ghe": "chair", "giuong": "bed", "ban": "dining table", "tv": "tv", "bep": "oven",
    "bon_rua": "sink", "tu_lanh": "refrigerator", "cay": "potted plant",
    "tu": "tu", "ke": "ke", "den": "den", "thao": "thao", "rem": "rem", "guong": "guong", "tranh": "tranh", "khac": "khac",
}
CATEGORIES = tuple(CATEGORY_LABEL)
MAX_ITEMS = 8  # asked of the AI

# Small things that crowd a photo and aren't what a studio points at
CLUTTER = {"bottle", "cup", "bowl", "book", "wine glass", "fork", "knife", "spoon", "remote", "cell phone", "person",
           "laptop", "mouse", "keyboard", "scissors", "toothbrush", "teddy bear", "hair drier", "handbag", "backpack",
           "umbrella", "banana", "apple", "orange", "sandwich", "cake", "donut", "pizza", "broccoli", "carrot", "hot dog",
           "sports ball", "tie", "suitcase"}
# Detector classes worth a hotspot even when the AI didn't name them
FURNITURE = {"couch", "chair", "bed", "dining table", "tv", "refrigerator", "oven", "sink", "toilet", "bench"}
MIN_CONFIDENCE = 0.4        # below this a detection is noise (369 of 1229 stored points were)
MIN_ALONE = 0.5             # a box the AI didn't confirm needs more
SAME_OBJECT = 0.5           # same label, intersection over the smaller box above this: one object
MAX_HOTSPOTS = 6


def _area(b) -> float:
    return max(0.0, b.x_max - b.x_min) * max(0.0, b.y_max - b.y_min)


def _overlap(a, b) -> float:
    w = min(a.x_max, b.x_max) - max(a.x_min, b.x_min)
    h = min(a.y_max, b.y_max) - max(a.y_min, b.y_min)
    small = min(_area(a), _area(b))
    return (max(0.0, w) * max(0.0, h)) / small if small else 0.0


def _inside(it, b) -> bool:
    return b.x_min <= it.x <= b.x_max and b.y_min <= it.y <= b.y_max


def propose(detected: list, items: list) -> list:
    """detected: DetectedFurniture from the detector (boxed); items: AiItem from the classifier.
    -> at most MAX_HOTSPOTS DetectedFurniture: merged (AI name + point, detector box) first, then AI-only, then
    detector-only furniture; larger first within a group. A box is used for one item at most."""
    from pipeline.schemas import DetectedFurniture

    # 1-2. clean the detector's boxes and drop duplicates, most confident first
    boxes = sorted((o for o in detected if o.bbox is not None and o.label not in CLUTTER
                    and (o.confidence or 0) >= MIN_CONFIDENCE), key=lambda o: -(o.confidence or 0))
    kept = []
    for o in boxes:
        if not any(k.label == o.label and _overlap(k.bbox, o.bbox) > SAME_OBJECT for k in kept):
            kept.append(o)

    # 3-4. each AI item takes the smallest compatible box holding its point, else stands alone
    used, merged, alone = set(), [], []
    for it in items:
        label = CATEGORY_LABEL.get(it.loai, it.loai)
        fits = [i for i, o in enumerate(kept) if i not in used and o.label == label and _inside(it, o.bbox)]
        if fits:
            i = min(fits, key=lambda i: _area(kept[i].bbox))
            used.add(i)
            o = kept[i]
            merged.append(DetectedFurniture(label=o.label, label_vi=it.ten, confidence=o.confidence, bbox=o.bbox,
                                            hotspot_anchor=(it.x, it.y), nguon_ai="ca_hai"))
        else:
            alone.append(DetectedFurniture(label=label, label_vi=it.ten, hotspot_anchor=(it.x, it.y), nguon_ai="gemini"))

    # 5. boxes the AI didn't name: furniture only, and surer
    solo = [o.model_copy(update={"nguon_ai": "yolo"}) for i, o in enumerate(kept)
            if i not in used and o.label in FURNITURE and (o.confidence or 0) >= MIN_ALONE]

    # 6. order, one point per distinct item (six identical dining chairs are one item), cap
    by_size = lambda o: -_area(o.bbox)  # noqa: E731
    named = {o.label for o in merged + alone}
    out, seen = [], set()
    for o in sorted(merged, key=by_size) + alone + [o for o in sorted(solo, key=by_size) if o.label not in named]:
        key = " ".join(o.label_vi.lower().split()) if o.nguon_ai != "yolo" and o.label_vi else o.label
        if key not in seen:
            seen.add(key)
            out.append(o)
    return out[:MAX_HOTSPOTS]


def with_proposed(furniture_res, classification):
    """The detection result with its objects replaced by the proposed hotspots; counts_by_category stays the raw
    detector's (the classifier's evidence). classification may be None or carry no items (offline fallback)."""
    items = getattr(classification, "items", None) or []
    return furniture_res.model_copy(update={"objects": propose(furniture_res.objects, items)})
