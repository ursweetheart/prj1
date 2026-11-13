"""Demo behaviour for the trend dashboard — SIMULATED, never real traffic.

    python -m pipeline.demo_activity              # (re)create ~8 weeks of demo sessions, one style rising
    python -m pipeline.demo_activity --remove     # delete every demo session and its events, nothing else

Every session id starts with 'demo-' (the /events endpoint refuses that prefix, so real data can never collide).
While any exist the dashboard shows "Đang hiển thị cả dữ liệu mô phỏng", and taxonomy discovery ignores them.
Remove before real use."""

import argparse
import random
import uuid
from datetime import datetime, timedelta, timezone

import psycopg

from pipeline.store import DSN

PREFIX = "demo-"
DAYS, SESSIONS, SAVE_RATE = 56, 240, 0.2
# share of sessions drawn to the rising style, by week (0 = last 7 days): it takes off in the last two weeks
RISING_PULL = {0: 0.8, 1: 0.3}
BASE_PULL = 0.05

SNAPSHOT = ("SELECT s.id, COALESCE((SELECT array_agg(d.ma_dinh_danh || ':' || v.ma_dinh_danh) FROM space_gia_tri sg "
            "JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id "
            "WHERE sg.space_id = s.id), '{}'), s.design_style FROM space s WHERE s.review_status = 'published'")


def remove(conn) -> int:
    """Delete demo sessions (their events go with them: ON DELETE CASCADE)."""
    return conn.execute("DELETE FROM phien_truy_cap WHERE id LIKE %s", (PREFIX + "%",)).rowcount


def generate(conn, sessions: int = SESSIONS, seed: int = 42, now: datetime | None = None) -> dict:
    """Replace the demo activity. Returns what was made, including which style was made to rise."""
    rnd = random.Random(seed)
    now = now or datetime.now(timezone.utc)
    remove(conn)
    spaces = conn.execute(SNAPSHOT).fetchall()  # (id, tags, design_style) — tags exactly as /events snapshots them
    if not spaces:
        raise SystemExit("no published space: publish some first (/quan-tri)")
    by_style = {}
    for s in spaces:
        if s[2] and s[2].lower() != "khac":
            by_style.setdefault(s[2], []).append(s)
    ranked = sorted(by_style, key=lambda k: (-len(by_style[k]), k))
    rising = ranked[1] if len(ranked) > 1 else ranked[0]  # not the usual leader, so the rise is visible

    made_sessions, views, saves = 0, 0, 0
    weeks = DAYS // 7
    for k in range(sessions):  # the same number of sessions every week, so the rise is not lost in random traffic
        week = k % weeks
        start = now - timedelta(days=week * 7 + rnd.uniform(0.01, 6.99))
        pull = RISING_PULL.get(week, BASE_PULL)
        taste = rising if rnd.random() < pull else rnd.choice(ranked)
        sid = PREFIX + uuid.UUID(int=rnd.getrandbits(128)).hex
        conn.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap, created_at) VALUES (%s, true, %s)", (sid, start))
        picks = [rnd.choice(by_style[taste]) if rnd.random() < 0.7 else rnd.choice(spaces) for _ in range(rnd.randint(3, 10))]
        rows = []
        for n, (space_id, tags, _) in enumerate(picks):
            at = start + timedelta(minutes=2 * n)
            rows.append((sid, "xem_khong_gian", space_id, tags, at))
            if rnd.random() < SAVE_RATE:
                rows.append((sid, "luu_anh", space_id, tags, at + timedelta(seconds=30)))
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri, created_at) VALUES (%s,%s,%s,%s,%s)", rows)
        made_sessions += 1
        views += sum(r[1] == "xem_khong_gian" for r in rows)
        saves += sum(r[1] == "luu_anh" for r in rows)
    return {"sessions": made_sessions, "views": views, "saves": saves, "rising_style": rising}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remove", action="store_true", help="delete all demo sessions and stop")
    ap.add_argument("--sessions", type=int, default=SESSIONS)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    with psycopg.connect(DSN) as conn:
        if a.remove:
            print(f"removed {remove(conn)} demo sessions")
        else:
            r = generate(conn, a.sessions, a.seed)
            print(f"SIMULATED: {r['sessions']} demo sessions, {r['views']} views, {r['saves']} saves; "
                  f"rising style: {r['rising_style']}. Remove with: python -m pipeline.demo_activity --remove")


if __name__ == "__main__":
    main()
