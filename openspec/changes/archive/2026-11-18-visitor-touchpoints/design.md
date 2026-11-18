# Design

## Context

- **Collections:**
  - `SaveHeart.vue` toggles a photo in `lib/collection.js` (browser storage when signed out, `bo_suu_tap` `dang_luu` when signed in);
  - `/bo-suu-tap` is `CollectionView.vue`;
  - sent briefs are snapshots `bo_suu_tap` `da_gui` with a share code, readable at `GET /collections/shared/{code}` (page `/bo-suu-tap/xem/:ma`);
  - `bo_suu_tap.loai` CHECK is `('dang_luu','da_gui')`.
- **Estimate:** `pipeline/estimate.py` `estimate()` returns the range and the breakdown, and already lists "dự án cùng loại". `du_an` has `loai`, `muc_dau_tu` (a `muc_dau_tu` taxonomy code: `duoi_300tr`, `300tr_700tr`, `700tr_1500tr`, `tren_1500tr`) and `dien_tich_m2`; today 0 of 65 projects have a budget or an area.
- **Quiz:** `quiz.suggest_projects` already returns `du_an` with the result, and `QuizView.vue` doesn't show it.
- **Leads:**
  - `notify.notify_new_lead` and `confirm_to_visitor` run as BackgroundTasks from chat, form, brief and estimate;
  - the chat lead path is in `assistant.respond`;
  - the maintenance loop (`_weekly_once`) runs every 10 minutes.

## Decisions

### 1. Save prompt

`SaveHeart.vue`, after a successful add while `!session.token`, when `sessionStorage d3_moi_dang_ky` is unset:
- sets the flag;
- shows a `role="status"` note next to the heart, with a router-link to `/dang-nhap?next=<current path>`;
- the note closes on its ✕ or after 8 s.

### 2. Share snapshot

`POST /collections/share {space_ids ≤ 60}` (public, rate limit 10 per 60 s):
1. Keep only published ids, in order.
2. Insert `bo_suu_tap` with `loai='chia_se'`, a random code (same generator as briefs) and its photos.
3. Return `{ma}`.

`GET /collections/shared/{code}` accepts `chia_se` as well as `da_gui`. The CHECK constraint is extended. The share event `chia_se` with object `bo_suu_tap` is tracked.

### 3. Budget-matched projects

- **Ranges in VND:** parsed from the `muc_dau_tu` codes (`duoi_Xtr`, `Xtr_Ytr`, `tren_Xtr`; `tr` = 10^6). Values that don't parse are ignored.
- **Overlap:** a project overlaps when its range intersects `[tong.min, tong.max]`.
- **Choice:**
  1. Published projects (≥ 1 published photo) that overlap, same type first, then the rest; up to 3.
  2. If none, published projects of `loai = loai_nha` under the fallback label.
- **Response:** `du_an_goi_y: {nhan, ds: [{slug, ten, co_trang, anh}]}`. The old "same type" list is replaced by this.

### 4. Quiz projects

`QuizView.vue` renders `result.du_an`: a link to `/du-an/<slug>` when `co_trang`, else to `/khong-gian/<anh.id>`.

### 5. Working hours

- `pipeline/hours.py`: `D3_GIO_LAM_VIEC` (default `T2-T7 08:00-17:30`) and `next_open(now) -> datetime | None` (None = open now). Zone `Asia/Ho_Chi_Minh`.
- In the chat lead path: when `next_open(now)` is not None:
  - `lead.thong_bao_luc = next_open`;
  - the answer appends the expected-time sentence;
  - `notify_new_lead` is not scheduled.
- The maintenance loop sends `notify_new_lead` for leads with `thong_bao_luc <= now AND NOT da_thong_bao`, then sets `da_thong_bao`. `notify_new_lead` sets `da_thong_bao` too, so nothing is ever sent twice.

### 6. SMS

`notify.send_sms(phone, text, lead_id)`:
- **Provider:** env `D3_SMS_URL` + `D3_SMS_TOKEN` (generic JSON POST `{to, content}` with Bearer auth; most Vietnamese gateways offer this shape).
- **Without a provider:** no HTTP call.
- **Log:** always a row in `tin_nhan_sms(lead_id, so_che, noi_dung, trang_thai, loi, luc)`, with the number masked except its last 3 digits.
- **Called from** `confirm_to_visitor` when the lead has a phone.

## Risks / Trade-offs

- **[No real SMS provider yet]** The channel and the log are ready, and the operator sets two env vars. This is stated in the admin docs.
- **[Budget matching has no data yet]** The fallback is labelled honestly, and staff can fill `muc_dau_tu` per project with `PUT /projects/{slug}`.
- **[Deferred notification delays the team]** That's act-4's intent: no one is on duty outside hours. The visitor is told the time.
