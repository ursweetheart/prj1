## Why

QT-01 (M5) is the path from an architect's photos to a published space, but `/quan-tri` only covers its middle: staff can fix `space_type` / `design_style` and advance one space at a time. New photos still enter through `python ingest.py`, the AI caption/alt/materials and detected hotspots cannot be corrected, the `content` role and the image-rights check ("Cleared") do not exist, and the two dimensions the AI cannot see (loại công trình, mức đầu tư) have no way in — so none of the 152 spaces is published and the 6-facet portfolio has nothing to show. NFR-12 (a 40-photo project in under 20 minutes) is out of reach one photo and one click at a time.

## What Changes

- **Upload a project in bulk**: `POST /spaces/ingest` takes an optional `project` name; images land in `image_d3/<project_folder>/`, so the folder groups a project's spaces (empty name → `uploads/` as today). The review page gets a multi-file upload with a project name, sequential sends (single GPU), progress and per-file errors.
- **Edit AI content**: `PATCH /spaces/{id}` also accepts `caption`, `alt_text`, `materials`; every change is written to `review_log`. Editing materials re-tags `vat_lieu` through the existing `sync_ai_tags` trigger.
- **Content role**: `content` may edit `caption` / `alt_text` of spaces in `in_review`, and nothing else.
- **Human tags**: set the values of human-only dimensions (`loai_cong_trinh`, `muc_dau_tu`) on a list of spaces, validated against the taxonomy, stored with `nguon_tao='nguoi'`; the UI offers "apply to the whole project".
- **Cleared state** — **BREAKING** for the status order: `draft → in_review → approved → cleared → published`. Advancing to `cleared` requires an explicit confirmation that the client allowed the photos to be published.
- **Hotspot confirmation**: staff delete wrongly detected objects or rename their label; the public detail page shows only what remains.
- **Bulk advance**: advance several spaces (or a whole project) one step in one request, with the same role rules as a single advance.

Out of scope: the "track results after 30 days" step of QT-01 (needs behaviour data, belongs to the trend dashboard).

## Capabilities

### New Capabilities
- `publishing-console`: the staff review page `/quan-tri` — bulk project upload, editing AI content and tags, hotspot confirmation, bulk advance, role-aware controls.

### Modified Capabilities
- `space-review-api`: ingest takes a project name; review workflow gains `cleared`, the rights confirmation, the `content` role, editable caption/alt/materials, human tags, hotspot edits and bulk advance.

## Impact

- `backend/api.py`: `ingest`, `Review` model and `PATCH /spaces/{id}`, new tag and bulk-advance endpoints, `NEXT` order.
- `backend/auth.py`: `content` joins the roles allowed to edit text.
- `backend/schema.sql`: nothing new (`space_gia_tri.nguon_tao`, `hotspots jsonb` and `review_log` already exist).
- `src/views/ReviewView.vue`, `src/api.js` (`NEXT_STATUS`, `STATUS_VI`, upload / tag / bulk helpers).
- Existing published spaces: none yet, so the new state needs no data migration.
