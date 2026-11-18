"""Nightly processing into the analytics store (tracking-pipeline; seq-4 loop "Hằng đêm" b6-b11, act-3, dfd-2-5 5.2/5.3).

For every complete day (UTC+7) not processed yet, in one transaction:
  1. enrich: an event about a space without design attributes gets the space's current values, a project view gets
     the values of the project's published spaces (values captured when the event happened are kept);
  2. real dwell time: the time the browser measured, else the time to the session's next event, at most 30 minutes;
  3. abnormal sessions (> 500 events in the day, >= 60 in one minute, or >= 20 page views all under 1 s) are recorded
     and left out of every aggregate;
  4. daily aggregates: per taxonomy value, per space, per behaviour type and page / object, briefs and leads.
Then the interest score and trend of the last processed day are stored (tk_xu_huong) and taste groups are computed.
The store holds no session id. The current day is never processed. Re-running a day replaces its figures.

    python -m pipeline.rollup                 # every pending day
    python -m pipeline.rollup --ngay 2026-11-10 2026-11-11   # reprocess these days
"""

import argparse
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb

from pipeline import trends
from pipeline.store import DSN

log = logging.getLogger("d3.rollup")
TZ = "Asia/Ho_Chi_Minh"
LOCAL = ZoneInfo(TZ)
DAY = f"(e.created_at AT TIME ZONE '{TZ}')::date"
MAX_DWELL_MS = 30 * 60 * 1000
MAX_EVENTS_PER_DAY, BURST_PER_MINUTE, FAST_VIEWS, FAST_MS = 500, 60, 20, 1000
VIEW_TYPES = ("xem_trang", "xem_du_an")
SIMILAR_TYPES = ("xem_goi_y_tuong_tu", "chon_goi_y")  # counted per day, not per object
MAX_DAYS_BACK = 400
RUN_FROM_HOUR = 1
LOCK_KEY = 4_200_101  # pg advisory lock: never two runs at once


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def local_today(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(LOCAL).date()


def pending_days(conn, now: datetime | None = None) -> list[date]:
    """Complete days from the earliest raw row (at most MAX_DAYS_BACK ago) up to yesterday, not processed yet."""
    yesterday = local_today(now) - timedelta(days=1)
    first = _rows(conn, f"""SELECT min(d) FROM (
        SELECT min((created_at AT TIME ZONE '{TZ}')::date) d FROM su_kien UNION ALL
        SELECT min((created_at AT TIME ZONE '{TZ}')::date) FROM bo_suu_tap WHERE loai = 'da_gui' UNION ALL
        SELECT min((created_at AT TIME ZONE '{TZ}')::date) FROM lead UNION ALL
        SELECT min(ngay) FROM su_kien_an_danh) x""")[0][0]
    if first is None:
        return []
    first = max(first, yesterday - timedelta(days=MAX_DAYS_BACK))
    done = {d for (d,) in _rows(conn, "SELECT ngay FROM tk_ngay WHERE ngay BETWEEN %s AND %s", (first, yesterday))}
    return [first + timedelta(days=i) for i in range((yesterday - first).days + 1) if first + timedelta(days=i) not in done]


def _enrich(conn, d):
    conn.execute(f"""UPDATE su_kien e SET gia_tri = v.vals FROM (
        SELECT sg.space_id, array_agg(DISTINCT c.ma_dinh_danh || ':' || g.ma_dinh_danh) vals
          FROM space_gia_tri sg JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id JOIN chieu_phan_loai c ON c.id = g.chieu_id
         GROUP BY sg.space_id) v
        WHERE v.space_id = e.space_id AND e.gia_tri = '{{}}' AND {DAY} = %s""", (d,))
    conn.execute(f"""UPDATE su_kien e SET gia_tri = v.vals FROM (
        SELECT s.du_an_slug, array_agg(DISTINCT c.ma_dinh_danh || ':' || g.ma_dinh_danh) vals
          FROM space s JOIN space_gia_tri sg ON sg.space_id = s.id JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id
          JOIN chieu_phan_loai c ON c.id = g.chieu_id
         WHERE s.review_status = 'published' AND s.du_an_slug IS NOT NULL GROUP BY s.du_an_slug) v
        WHERE e.loai = 'xem_du_an' AND v.du_an_slug = e.doi_tuong AND e.gia_tri = '{{}}' AND {DAY} = %s""", (d,))


def _dwell(conn, d):
    conn.execute(f"""UPDATE su_kien t SET dung_thuc_ms = x.ms FROM (
        SELECT r.id, (SELECT LEAST(raw, %s) WHERE raw IS NOT NULL)::int AS ms, ngay FROM (  -- LEAST ignores NULL: keep None
          SELECT e.id, COALESCE(e.thoi_gian_dung_ms, round(1000 * extract(epoch FROM lead(e.created_at) OVER w - e.created_at))) raw,
                 {DAY} AS ngay
          FROM su_kien e
         WHERE e.phien_id IN (SELECT DISTINCT phien_id FROM su_kien e WHERE {DAY} = %s)
        WINDOW w AS (PARTITION BY e.phien_id ORDER BY e.created_at)) r) x
        WHERE t.id = x.id AND x.ngay = %s""", (MAX_DWELL_MS, d, d))


def _abnormal(conn, d):
    conn.execute("DELETE FROM phien_bat_thuong WHERE ngay = %s", (d,))
    conn.execute(f"""INSERT INTO phien_bat_thuong (ngay, phien_id, ly_do)
        SELECT %(d)s, phien_id, string_agg(ly_do, ', ') FROM (
          SELECT phien_id, 'qua_nhieu_su_kien' ly_do FROM su_kien e WHERE {DAY} = %(d)s
           GROUP BY phien_id HAVING count(*) > %(max)s
          UNION ALL
          SELECT DISTINCT phien_id, 'don_dap_trong_mot_phut' FROM (
            SELECT phien_id FROM su_kien e WHERE {DAY} = %(d)s
             GROUP BY phien_id, date_trunc('minute', created_at) HAVING count(*) >= %(burst)s) b
          UNION ALL
          SELECT phien_id, 'xem_qua_nhanh' FROM su_kien e WHERE {DAY} = %(d)s AND loai = ANY(%(views)s)
           GROUP BY phien_id HAVING count(*) >= %(fast)s AND bool_and(COALESCE(thoi_gian_dung_ms, 0) < %(fast_ms)s)
        ) r GROUP BY phien_id""",
                 {"d": d, "max": MAX_EVENTS_PER_DAY, "burst": BURST_PER_MINUTE, "views": list(VIEW_TYPES),
                  "fast": FAST_VIEWS, "fast_ms": FAST_MS})


def _aggregate(conn, d) -> tuple[int, int, int]:
    kept = f"""FROM su_kien e WHERE {DAY} = %(d)s
                 AND NOT EXISTS (SELECT 1 FROM phien_bat_thuong b WHERE b.ngay = %(d)s AND b.phien_id = e.phien_id)"""
    a = {"d": d}
    for t in ("tk_gia_tri_ngay", "tk_khong_gian_ngay", "tk_hanh_vi_ngay", "tk_tong_ngay"):
        conn.execute(f"DELETE FROM {t} WHERE ngay = %(d)s", a)
    conn.execute(f"""INSERT INTO tk_gia_tri_ngay (ngay, gia_tri, so_xem, so_luu, so_phien, tong_dung_ms)
        SELECT %(d)s, v, count(*) FILTER (WHERE loai = 'xem_khong_gian'), count(*) FILTER (WHERE loai = 'luu_anh'),
               count(DISTINCT phien_id), COALESCE(sum(dung_thuc_ms) FILTER (WHERE loai = 'xem_khong_gian'), 0)
          FROM (SELECT e.loai, e.phien_id, e.dung_thuc_ms, unnest(e.gia_tri) v {kept}
                   AND e.loai IN ('xem_khong_gian', 'luu_anh')) x
         GROUP BY v""", a)
    # briefs carry no snapshot: the sent photos' current values (as trends did before)
    conn.execute(f"""INSERT INTO tk_gia_tri_ngay (ngay, gia_tri, so_brief)
        SELECT %(d)s, c.ma_dinh_danh || ':' || g.ma_dinh_danh, count(*)
          FROM bo_suu_tap b JOIN bo_suu_tap_anh ba ON ba.bo_suu_tap_id = b.id
          JOIN space_gia_tri sg ON sg.space_id = ba.space_id JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id
          JOIN chieu_phan_loai c ON c.id = g.chieu_id
         WHERE b.loai = 'da_gui' AND (b.created_at AT TIME ZONE '{TZ}')::date = %(d)s GROUP BY 2
        ON CONFLICT (ngay, gia_tri) DO UPDATE SET so_brief = EXCLUDED.so_brief""", a)
    conn.execute(f"""INSERT INTO tk_khong_gian_ngay (ngay, space_id, so_xem, so_luu)
        SELECT %(d)s, space_id, count(*) FILTER (WHERE loai = 'xem_khong_gian'), count(*) FILTER (WHERE loai = 'luu_anh')
          {kept} AND loai IN ('xem_khong_gian', 'luu_anh') AND space_id IS NOT NULL GROUP BY space_id""", a)
    conn.execute(f"""INSERT INTO tk_hanh_vi_ngay (ngay, loai, trang, doi_tuong, so_luot, tong_dung_ms, so_co_dung, tong_cuon, so_co_cuon)
        SELECT %(d)s, loai, trang, doi_tuong, count(*), COALESCE(sum(dung), 0), count(dung), COALESCE(sum(cuon), 0), count(cuon)
          FROM (SELECT e.loai, COALESCE(e.trang, '') trang,
                       CASE WHEN e.loai = ANY(%(similar)s) THEN '' ELSE COALESCE(e.doi_tuong, '') END doi_tuong,
                       CASE WHEN e.loai = ANY(%(views)s) THEN e.dung_thuc_ms END dung, e.do_sau_cuon cuon
                  {kept} AND e.loai NOT IN ('xem_khong_gian', 'luu_anh', 'chon_trac_nghiem', 'ap_dung_bo_loc')
                UNION ALL
                SELECT 'ap_dung_bo_loc', '', v, NULL, NULL
                  FROM (SELECT unnest(e.gia_tri) v {kept} AND e.loai = 'ap_dung_bo_loc') f) x
         GROUP BY loai, trang, doi_tuong""", {**a, "similar": list(SIMILAR_TYPES), "views": list(VIEW_TYPES)})
    leads = dict(_rows(conn, f"SELECT nguon, count(*) FROM lead WHERE (created_at AT TIME ZONE '{TZ}')::date = %s GROUP BY 1", (d,)))
    briefs = _rows(conn, f"SELECT count(*) FROM bo_suu_tap WHERE loai = 'da_gui' AND (created_at AT TIME ZONE '{TZ}')::date = %s",
                   (d,))[0][0]
    conn.execute("INSERT INTO tk_tong_ngay (ngay, so_brief, lead) VALUES (%s, %s, %s)", (d, briefs, Jsonb(leads)))
    n_events, n_sessions = _rows(conn, f"SELECT count(*), count(DISTINCT phien_id) FROM su_kien e WHERE {DAY} = %s", (d,))[0]
    n_bad = _rows(conn, "SELECT count(*) FROM phien_bat_thuong WHERE ngay = %s", (d,))[0][0]
    return n_events, n_sessions, n_bad


def process_day(conn, d: date):
    _enrich(conn, d)
    _dwell(conn, d)
    _abnormal(conn, d)
    n_events, n_sessions, n_bad = _aggregate(conn, d)
    conn.execute("INSERT INTO tk_ngay (ngay, xu_ly_luc, so_su_kien, so_phien, so_phien_bat_thuong) VALUES (%s, now(), %s, %s, %s) "
                 "ON CONFLICT (ngay) DO UPDATE SET xu_ly_luc = now(), so_su_kien = EXCLUDED.so_su_kien, "
                 "so_phien = EXCLUDED.so_phien, so_phien_bat_thuong = EXCLUDED.so_phien_bat_thuong",
                 (d, n_events, n_sessions, n_bad))


def store_trends(conn, d: date) -> int:
    """seq-4 b11: each value's score in the 7 days up to d against the average of the 4 weeks before, with its label."""
    weekly, signals0 = defaultdict(lambda: [0] * (trends.WEEKS_BACK + 1)), defaultdict(int)
    for v, w, xem, luu, brief in _rows(conn, "SELECT gia_tri, (%s - ngay) / 7, sum(so_xem), sum(so_luu), sum(so_brief) "
                                              "FROM tk_gia_tri_ngay WHERE ngay > %s - %s AND ngay <= %s GROUP BY 1, 2",
                                       (d, d, 7 * (trends.WEEKS_BACK + 1), d)):
        weekly[v][w] += trends.score(xem, luu, brief)
        if w == 0:
            signals0[v] += xem + luu + brief
    conn.execute("DELETE FROM tk_xu_huong WHERE ngay_tinh = %s", (d,))
    for v, wk in weekly.items():
        t = trends.trend(wk, signals0[v])
        conn.execute("INSERT INTO tk_xu_huong (ngay_tinh, gia_tri, tuan0, tb4, so_tin_hieu, thay_doi, xu_huong) "
                     "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                     (d, v, wk[0], sum(wk[1:]) / trends.WEEKS_BACK, signals0[v], t["thay_doi"], t["xu_huong"]))
    return len(weekly)


def run(days: list[date] | None = None, now: datetime | None = None) -> list[date]:
    """Process the given days (or every pending one), then store the trends and taste groups of the last processed day."""
    from pipeline import taste_groups
    with psycopg.connect(DSN) as conn:
        todo = sorted(set(days)) if days is not None else pending_days(conn, now)
        today = local_today(now)
        todo = [d for d in todo if d < today]  # the current day is never processed
        for d in todo:
            with conn.transaction():
                process_day(conn, d)
        last = _rows(conn, "SELECT max(ngay) FROM tk_ngay")[0][0]
        if todo and last:
            with conn.transaction():
                store_trends(conn, last)
                taste_groups.run(conn, last)
    if todo:
        log.info("rollup: %d day(s) processed, last %s", len(todo), last)
    return todo


def due_and_run(now: datetime | None = None) -> list[date]:
    """The nightly check (called every 10 minutes): from 01:00 UTC+7 once yesterday is missing, under an advisory lock."""
    now = now or datetime.now(timezone.utc)
    if now.astimezone(LOCAL).hour < RUN_FROM_HOUR:
        return []
    with psycopg.connect(DSN, autocommit=True) as lock:
        yesterday = local_today(now) - timedelta(days=1)
        if _rows(lock, "SELECT 1 FROM tk_ngay WHERE ngay = %s", (yesterday,)):
            return []
        if not _rows(lock, "SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))[0][0]:
            return []
        try:
            return run(now=now)
        finally:
            lock.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ngay", nargs="*", type=date.fromisoformat, help="reprocess these days (YYYY-MM-DD)")
    args = ap.parse_args()
    done = run(args.ngay if args.ngay else None)
    print(f"processed {len(done)} day(s)" + (f": {done[0]} .. {done[-1]}" if done else ""))
