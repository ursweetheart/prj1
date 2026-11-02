## Context

The review API (`PATCH /spaces/{id}`, `POST /spaces/ingest`) and page (`src/views/ReviewView.vue`) come from the archived change `ai-space-search-and-review`. Since then the taxonomy moved into the database (`discover-taxonomy-dimensions`): `space_gia_tri` holds every space's facet values, a trigger `sync_ai_tags` mirrors the AI columns (`space_type`, `design_style`, `palette`, `materials`) into it, and rows with `nguon_tao='nguoi'` are left alone. The portfolio filters on 6 dimensions, two of which (`loai_cong_trinh`, `muc_dau_tu`) only a human can fill. The project runs on one machine for a course demo; there is one GPU, so ingest stays synchronous.

## Goals / Non-Goals

**Goals:**
- Every QT-01 step up to "Published" can be done from `/quan-tri`.
- A 40-photo project can be uploaded, tagged and pushed through review with a handful of actions (NFR-12).
- Role rules stay enforced on the server; the UI only hides what the server would refuse.

**Non-Goals:**
- Post-publication tracking (30-day results) — trend dashboard.
- Background job queue for ingest; per-user upload quotas.
- A separate project entity: the image folder is the project.

## Decisions

**Project = image folder.** `ingest` takes `project` (form field), folds it to `[a-z0-9_]` (`project_folder`) and stores the file in `image_d3/<folder>/`. `relative_path` and `subfolder` already derive from the folder, so cards, grouping and "apply to the whole project" need no new table. *Alternative:* a `project` table with FK from `space` — more correct for M2's project sheet, but nothing reads project attributes yet. Upload of the same file name into the same project replaces the space (upsert on `relative_path`), which is the natural "re-upload".

**Sequential upload from the browser.** The page sends one file per request and waits; the server keeps processing synchronous. *Alternative:* one multi-file request — a single failure would lose the batch, and the request would run for minutes. Per-file requests give progress and per-file errors for free.

**Text edits go through the existing PATCH.** `Review` gains `caption`, `alt_text`, `materials`; changed fields are logged with before/after like facet edits. Changing `materials` re-tags `vat_lieu` through the trigger, no extra code.

**Content role is a narrow exception.** `PATCH` accepts `content` as well as STAFF; for `content` the request is refused (403) unless the space is `in_review` and only `caption` / `alt_text` are sent. Advancing stays STAFF-only.

**Human tags endpoint.** `PUT /spaces/tags` `{space_ids | project, dimension, values}` replaces the `nguoi` rows of that dimension for those spaces in one transaction. It refuses (422) AI-mirrored dimensions — those are edited through their columns, otherwise the trigger would fight the edit — unknown values, and more than one value for a single-value dimension. STAFF only.

**Cleared state.** `NEXT` becomes `draft → in_review → approved → cleared → published`. Moving `approved → cleared` requires `rights_confirmed: true` (else 422) and is logged with that flag; like approving and publishing it needs `lead_architect` / `admin`.

**Hotspots: keep-list, not free edit.** `PATCH` accepts `hotspots: [{index, label_vi}]`: the server keeps the detected objects at those indexes, in that order, with the new `label_vi`. Staff can remove and rename but cannot invent coordinates, so the stored shape stays what the detector produced and `HotspotImage` needs no change.

**Bulk advance is all-or-nothing.** `POST /spaces/advance` `{space_ids, rights_confirmed}` applies the single-advance rules to each space inside one transaction; any failure (409 final state, 403 role, 422 missing confirmation) rolls back all and names the offending id. The single-space advance and the bulk one share one helper. *Alternative:* partial success with a per-id report — harder to explain in the UI; the page lists one status tab at a time, so a selection is homogeneous anyway.

## Risks / Trade-offs

- [Two uploads with different project names that fold to the same folder merge] → acceptable; the folded name is shown after upload.
- [Folder rename is impossible without moving files and rewriting `relative_path`] → out of scope; pick the name at upload.
- [Inserting `cleared` changes the status order clients rely on] → only `ReviewView` reads `NEXT_STATUS`; it is updated in the same change. No space is published yet, so no data moves.
- [Sequential upload of 40 photos takes as long as 40 pipeline runs] → progress bar; the architect can keep reviewing other tabs meanwhile.

## Migration Plan

No schema change. Re-run nothing; deploy is "restart uvicorn, reload the page". Rollback: revert the commit — spaces already in `cleared` would need `UPDATE space SET review_status='approved' WHERE review_status='cleared'`.
