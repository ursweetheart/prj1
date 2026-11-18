"""python ingest_projects.py [--dry-run] [--limit N] [slug ...] -> kept for the documented command (project-space-sync).

Same as `python sync_projects.py --ingest`: site photos already stored (under any folder name) are matched, not
analysed again; only unmatched ones become draft spaces in <slug with _>/<file>. Nothing is published.
"""
import sys

import sync_projects

if __name__ == "__main__":
    sys.argv = [sys.argv[0], *([] if "--dry-run" in sys.argv else ["--ingest"]), *sys.argv[1:]]
    sync_projects.main()
