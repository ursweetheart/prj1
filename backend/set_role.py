"""Bootstrap/ops: python set_role.py user@example.com admin   (the account must have registered first)."""
import sys

import psycopg

from auth import ROLES
from pipeline.store import DSN

email, role = sys.argv[1].lower(), sys.argv[2]
assert role in ROLES, f"role must be one of {ROLES}"
with psycopg.connect(DSN) as c:
    n = c.execute("UPDATE app_user SET role=%s WHERE email=%s", (role, email)).rowcount
print("updated" if n else "no such user")
