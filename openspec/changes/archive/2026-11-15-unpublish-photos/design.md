# Design

## Context

- **Backward paths in `backend/api.py`.** `BACK = {action: (allowed sources, target, reason kind, log action)}` drives `_move_back()`:
  - it locks the rows, refuses the whole selection on one wrong status (409 naming it), writes `space.ly_do_duyet = {loai, ly_do, boi, luc}` and a `review_log` row per photo, then runs `notify.notify_returned` in the background;
  - its actions are `return` (in_review / approved / cleared → draft, `tra_ve`), `keep_internal` (approved / cleared → noi_bo, `noi_bo`) and `reopen` (noi_bo → draft, `mo_lai`).
- **Where the reason shows.** It is cleared when a photo is advanced. `GET /spaces?tra_ve=1` lists drafts whose reason kind is `tra_ve` or `mo_lai`, and `ly_do_duyet` is returned to staff only.
- **The review page** (`ReviewView.vue`, ours) has status chips, per-photo buttons ("Trả về nháp", "Lưu nội bộ", "Mở lại"), a bulk "Trả về nháp" and one reason dialog (`ask(action, ids, event)`, `ACTION_VI`, `CALL`). The card shows `REASON_VI[loai]` with the reason.
- **Public readers already filter `review_status = 'published'`:**
  - `GET /spaces/{id}` and `/spaces` for visitors;
  - search;
  - `/projects/{folder}/spaces`;
  - the quiz, chat example photos and `items.spaces_for`;
  - `project_stats`;
  - collections (`bo_suu_tap.items` / sent copies).

## Goals / Non-Goals

**Goals:**
- Take published photos down to draft or to internal, with the existing reason, log and notice machinery.
- Prove the photo leaves every public endpoint.

**Non-Goals:**
- Protecting the raw image files (see Risks).
- Scheduled take-downs.
- Rights expiry dates.
- Notifying visitors.

## Decisions

### 1. Two `BACK` entries, one endpoint
```python
"unpublish":          ({"published"}, "draft",  "go_xuong",  "unpublish"),
"unpublish_internal": ({"published"}, "noi_bo", "go_noi_bo", "unpublish"),
```
`POST /spaces/unpublish {space_ids, ly_do, giu_noi_bo: bool = false}` (APPROVERS) picks the entry and calls `_move_back`.
- The log row's detail already holds `from` / `to` / `reason`, so `published → draft` and `published → noi_bo` are both distinguishable.
- `reopen` keeps accepting `noi_bo` whatever brought it there.

**Why not widen `return` / `keep_internal`:** the spec's existing scenario says a return naming a published photo is refused. Keeping take-down separate means a bulk "Trả về nháp" on a mixed selection can't silently unpublish something.

### 2. Reason kinds
- `go_xuong`: the card shows "Đã gỡ khỏi website". It counts as a returned draft for the `tra_ve=1` filter, so the query becomes `IN ('tra_ve', 'mo_lai', 'go_xuong')`.
- `go_noi_bo`: the card shows "Gỡ khỏi website, lưu nội bộ".
- `notify.KIND_VI` gets both labels.

### 3. Review page
- **On the "Đã đăng" tab** (approvers only):
  - each card gets "Gỡ khỏi website";
  - the selection row gets "Gỡ khỏi website N mục". It is shown on this tab, since the bulk advance button doesn't exist there; the select-all checkboxes are enabled for approvers on this tab.
- **The dialog for action `unpublish`** adds a labelled radio group: "Gỡ xuống để sửa (về Nháp)" (default) or "Gỡ và lưu nội bộ (khách rút lại đồng ý)". It sends `giu_noi_bo`.
- **`REASON_VI`** gains `go_xuong` / `go_noi_bo`, with a distinct border colour (the warn colour for `go_xuong`, the danger colour for `go_noi_bo`, as `noi_bo` has today).

### 4. Public-trace test
One API test publishes a throw-away photo with taxonomy values, hotspots linked to a test item, a project folder, a saved-collection entry and a sent brief. It checks that each public reader lists the photo, takes it down, and checks that each no longer does:
- `/spaces/{id}` gives 404 for a visitor;
- `/spaces`, `/search`, `/projects/{folder}/spaces`, `/items/{id}/spaces`;
- `project_stats.overview`;
- the sent copy's photos and the saved list.

Then it publishes the photo again and checks that it is back in the saved list and the sent copy.

## Risks / Trade-offs

- **[Raw image files stay reachable at `/images/<path>`]** → This is true for every non-published photo today, drafts included. A person who saved the direct file URL can still open it. Fixing it means serving images only for published photos or to staff (signed URLs, or a token query for staff pages), which touches every image on the site, Tùng's pages included. It is recorded as a known issue and on the fixing list, not done here.
- **[Search embeddings and cached answers]** → Search queries filter by status at query time, and chat history stores no images, so nothing cached keeps the photo.
- **[Project publish date]** → `project_stats` takes the earliest publish row, so a re-published project keeps its first date. That is acceptable, and the age only grows.

## Migration Plan

- No schema change. Rebuild the backend and web.
- **Rollback:** remove the endpoint and buttons. Photos already taken down stay in draft or noi_bo, and can be advanced or reopened normally.
