"""Working hours (visitor-touchpoints; act-4 "Trong giờ làm việc?").

D3_GIO_LAM_VIEC, default "T2-T7 08:00-17:30" (Monday to Saturday, UTC+7). Days: T2..T7, CN; a range "T2-T7" or a list
"T2,T4,T6". Inside hours a chat lead is announced at once; outside, the visitor is told when to expect contact and the
team is notified when the next working period starts.
"""

import os
import re
from datetime import datetime, time, timedelta, timezone

VN = timezone(timedelta(hours=7))
DEFAULT = "T2-T7 08:00-17:30"
DAY = {"T2": 0, "T3": 1, "T4": 2, "T5": 3, "T6": 4, "T7": 5, "CN": 6}
NAME = ["thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật"]


def parse(spec: str | None = None) -> tuple[set, time, time]:
    spec = (spec or os.getenv("D3_GIO_LAM_VIEC") or DEFAULT).strip().upper()
    m = re.fullmatch(r"([A-Z0-9,\-]+)\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", spec)
    if not m:
        return parse(DEFAULT)
    days = set()
    for part in m[1].split(","):
        a, _, b = part.partition("-")
        if a not in DAY or (b and b not in DAY):
            return parse(DEFAULT)
        days |= set(range(DAY[a], DAY[b] + 1)) if b else {DAY[a]}
    return days, time(int(m[2]), int(m[3])), time(int(m[4]), int(m[5]))


def next_open(now: datetime | None = None, spec: str | None = None) -> datetime | None:
    """None while open; otherwise the start of the next working period (aware, UTC+7)."""
    days, start, end = parse(spec)
    local = (now or datetime.now(timezone.utc)).astimezone(VN)
    if local.weekday() in days and start <= local.time() < end:
        return None
    for i in range(8):
        d = local.date() + timedelta(days=i)
        at = datetime.combine(d, start, VN)
        if d.weekday() in days and at > local:
            return at
    return None  # no working day configured: treat as always open


def sentence(at: datetime) -> str:
    return f"Đội tư vấn sẽ liên hệ anh/chị từ {at:%H:%M} {NAME[at.weekday()]} ({at:%d/%m})."
