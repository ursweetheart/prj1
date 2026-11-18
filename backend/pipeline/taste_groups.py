"""Taste groups (tracking-pipeline; act-3 "Phân cụm phiên, phát hiện nhóm thị hiếu mới").

Consented, non-abnormal sessions of the last 30 processed days, each with at least 3 events carrying design attributes,
are clustered by those attributes (k-means on log-weighted, L2-normalised counts; k from 2 to 6 chosen by silhouette).
Each group keeps its share of sessions and its 3 most over-represented values ('khac' never). A group whose two
strongest values together led no group in the previous 28 days' runs is new. Stored without any session id.
"""

from collections import Counter
from datetime import date, timedelta

import numpy as np
from psycopg.rows import tuple_row

WINDOW_DAYS, MIN_EVENTS, MIN_SESSIONS = 30, 3, 10
K_MIN, K_MAX, TOP, MIN_IN_GROUP, NEW_LOOKBACK = 2, 6, 3, 0.2, 28


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def session_values(conn, d: date) -> dict[str, Counter]:
    """{session id: Counter of 'dimension:value'} for the qualifying sessions of the window ending at d."""
    out, events = {}, Counter()
    for pid, n_events, vals in _rows(conn, """
        SELECT e.phien_id, count(DISTINCT e.id), array_agg(v)
          FROM su_kien e CROSS JOIN LATERAL unnest(e.gia_tri) v
         WHERE (e.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date BETWEEN %s AND %s
           AND e.gia_tri <> '{}' AND lower(v) NOT LIKE '%%:khac'
           AND NOT EXISTS (SELECT 1 FROM phien_bat_thuong b WHERE b.phien_id = e.phien_id
                            AND b.ngay = (e.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date)
         GROUP BY e.phien_id""", (d - timedelta(days=WINDOW_DAYS - 1), d)):
        if n_events >= MIN_EVENTS:
            out[pid] = Counter(vals)
    return out


def groups(sessions: dict[str, Counter]) -> list[dict] | None:
    """[{so_phien, ty_le, gia_tri: [top values]}] largest first; None when there are too few sessions."""
    if len(sessions) < MIN_SESSIONS:
        return None
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    values = sorted({v for c in sessions.values() for v in c})
    index = {v: i for i, v in enumerate(values)}
    x = np.zeros((len(sessions), len(values)))
    for r, c in enumerate(sessions.values()):
        for v, n in c.items():
            x[r, index[v]] = np.log1p(n)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    best = None
    distinct = len(np.unique(x.round(6), axis=0))
    for k in range(K_MIN, min(K_MAX, len(sessions) - 1, distinct) + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(x)
        if len(set(labels)) < 2:
            continue
        s = silhouette_score(x, labels)
        if best is None or s > best[0]:
            best = (s, labels)
    if best is None:
        return None
    labels = best[1]
    present = x > 0
    overall = present.mean(axis=0)
    out = []
    for g in sorted(set(labels), key=lambda g: -(labels == g).sum()):
        member = present[labels == g]
        share_in = member.mean(axis=0)
        lift = np.divide(share_in, overall, out=np.zeros_like(share_in), where=overall > 0)
        order = sorted((i for i in range(len(values)) if lift[i] > 1 and share_in[i] >= MIN_IN_GROUP),
                       key=lambda i: (-lift[i], -share_in[i], values[i]))
        out.append({"so_phien": int(member.shape[0]), "ty_le": round(float(member.shape[0] / len(sessions)), 3),
                    "gia_tri": [values[i] for i in order[:TOP]]})
    return out


def signature(vals: list[str]) -> tuple:
    return tuple(sorted(vals[:2]))


def mark_new(found: list[dict], earlier: set[tuple]) -> list[dict]:
    for g in found:
        g["moi"] = len(g["gia_tri"]) >= 2 and signature(g["gia_tri"]) not in earlier
    return found


def run(conn, d: date) -> list[dict] | None:
    sessions = session_values(conn, d)
    found = groups(sessions)
    conn.execute("DELETE FROM tk_nhom_chay WHERE ngay_tinh = %s", (d,))  # cascades to its groups
    conn.execute("INSERT INTO tk_nhom_chay (ngay_tinh, so_phien, du_du_lieu) VALUES (%s, %s, %s)",
                 (d, len(sessions), found is not None))
    if found is None:
        return None
    earlier = {signature(list(v)) for (v,) in _rows(conn, "SELECT gia_tri FROM tk_nhom_thi_hieu WHERE ngay_tinh >= %s "
                                                           "AND ngay_tinh < %s", (d - timedelta(days=NEW_LOOKBACK), d))}
    for i, g in enumerate(mark_new(found, earlier)):
        conn.execute("INSERT INTO tk_nhom_thi_hieu (ngay_tinh, nhom, so_phien, ty_le, gia_tri, moi) VALUES (%s,%s,%s,%s,%s,%s)",
                     (d, i, g["so_phien"], g["ty_le"], g["gia_tri"], g["moi"]))
    return found
