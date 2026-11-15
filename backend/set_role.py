"""Bootstrap/ops: python set_role.py user@example.com admin   (the account must have registered first).
Creates the first admin; after that, roles are changed at /quan-tri/tai-khoan (change user-admin). Logged too."""
import sys

import psycopg
from psycopg.types.json import Jsonb

from auth import ROLES
from pipeline.store import DSN

email, role = sys.argv[1].lower(), sys.argv[2]
assert role in ROLES, f"role must be one of {ROLES}"
with psycopg.connect(DSN) as c:
    row = c.execute("SELECT id, role FROM app_user WHERE email=%s", (email,)).fetchone()
    if row:
        c.execute("UPDATE app_user SET role=%s WHERE id=%s", (role, row[0]))
        c.execute("INSERT INTO nhat_ky_tai_khoan (nguoi_dung_id, tai_khoan_id, hanh_dong, truoc, sau) "
                  "VALUES (NULL, %s, 'doi_vai_tro', %s, %s)", (row[0], Jsonb({"role": row[1]}), Jsonb({"role": role})))
print("updated" if row else "no such user")
