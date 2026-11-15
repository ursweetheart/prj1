# Design

## Context

- **Style.** Every space has `design_style`, and the `space_ai_tags` trigger copies it into `space_gia_tri` as `phong_cach:<value>`. So `design_style` and the tag always agree. Today there are 40 published spaces: Indochine 13, Luxury 13, Hiện đại 8 and Japandi 6. All of them have an embedding.
- **Embeddings.** `space.embedding` is SigLIP2 `vector(768)`. pgvector 0.8.7 supports `avg(vector)` and the `<=>` cosine distance. `pipeline/search.py` already ranks by `embedding <=> v`.
- **Events.** `POST /events` takes `loai` from a `Literal`, and `su_kien.loai` has a CHECK constraint. Without consent it bumps `su_kien_an_danh`. `src/api.js track()` sends the session id only with consent. `collection.js` skips events for staff.
- **Trends.** `pipeline/trends.overview` reads `su_kien` without filtering by type. It maps every non-view to "luu" and looks up `WEIGHTS[loai]`, so a new event type would miscount saves and raise a KeyError. `discovery._space_facts` already filters `loai = 'xem_khong_gian'`.
- **Sign-in.** `/dang-nhap?next=/path` returns to the page after sign-in. Account collections use `require(*ROLES)` plus the `SIGNED_IN` limiter. The browser-to-account merge pattern lives in `src/lib/collection.js`.
- **The `/khong-gian` filter** state lives in `useBrowse` (`selected`, `toggle`). It is not set from the URL today.

## Goals / Non-Goals

**Goals:**
- The client never decides the result: the server checks every photo and does the scoring.
- No new model, no training and no new dependency: tags for the style and the existing embeddings for the suggestions.
- The quiz keeps working as more photos are published, with no tuning.

**Non-Goals:**
- Storing quiz attempts on the server for anonymous visitors. A result is only stored when an account saves it.
- Rate limits beyond the existing per-endpoint limiter.
- Adaptive questions, where the next pair depends on earlier answers.

## Decisions

### 1. Stateless quiz: the client sends back the pairs it was shown
`GET /quiz` returns `{cau_hoi: [{a: tile, b: tile}, …]}`, with tiles shaped like `/spaces` rows. `POST /quiz/result` takes `{cap: [[a_id, b_id], …], chon: [id, …]}`.

The server checks the following:
- every id is a published space with a non-`Khac` style;
- the pairs hold no duplicate photo;
- each chosen id is in a different pair and is one of that pair's two photos;
- `2 ≤ len(chon) ≤ len(cap) ≤ 6`.

Any failure answers 422.

- *Why not a server-side attempt token?* That would need a table or signed state. The only thing a visitor can fake by inventing pairs is **their own** result, and every photo still has to be published, so no data leaks. A token can be added later without changing the API shape.

### 2. Pair building (`pipeline/quiz.py build_pairs(spaces, rnd, n=6)`)
1. Group the eligible photos by style. Keep only styles with at least 2 photos.
2. **Share out the 2n slots** one at a time. Each slot goes to the style with the fewest slots so far that still has an unused photo. Ties are broken at random. This is "as even as the photos allow".
3. **Pair the slots** by repeatedly matching the style with the most remaining slots against the next one, with random tie-break. If one style is left holding slots that have no partner, drop them and lower the count of questions. The number of pairs that can be made is `min(⌊T/2⌋, T − M)`, where T is the number of slots and M is the largest style's share. If this gives fewer than 4 pairs, `GET /quiz` answers 409 `{"detail": "chua_du_anh"}`. The page shows "chưa có đủ ảnh".
4. **Pick photos for each pair.** Choose a space type that both styles still have, preferring the most common one. If there is none, use any type. Draw one unused photo of each style.
5. Shuffle the order of the pairs and the left/right side of each pair.

`rnd` is a `random.Random`. The endpoint seeds it from `os.urandom`, and tests pass a fixed seed.

- *Alternative: random pairs and reject the ones that don't fit.* It is simpler, but it cannot guarantee the balance that the spec scenario requires (3/3/3/3).

### 3. Scoring (`score(shown, chosen)`)
- `points[style] / shown[style]` for each style, from the styles stored in the DB, never from the client.
- **Result:** the top 2 styles with points > 0. Ties are broken by more points, then by the style code.
- **Percent** = that style's score / the sum of all style scores, rounded. So the two shown percentages do not have to add up to 100. This matches the spec example: Japandi 50%, Hiện đại 33%.
- **Names** come from `gia_tri_phan_loai.ten` (dimension `phong_cach`).

### 4. Suggestions by embedding centroid
One query:

```sql
WITH c AS (SELECT avg(embedding) v FROM space WHERE id = ANY(:chosen))
SELECT … FROM space, c
WHERE review_status = 'published' AND design_style = ANY(:top)
  AND id <> ALL(:shown) AND embedding IS NOT NULL
ORDER BY embedding <=> c.v
LIMIT 8
```

- The average of SigLIP2 vectors is a reasonable "taste" vector for a few photos.
- *Alternative: rank only by tags.* It is cheaper but ignores what the visitor actually picked inside a style.
- A result row gets `{phong_cach: [{ma, ten, ti_le}], goi_y: [tile + design_style]}`.

### 5. Events: a new type that trends filter out
- `chon_trac_nghiem` is added to the `Event` `Literal` and to `su_kien_loai_check`.
- The client calls `trackQuizPick(id)` when a photo is chosen, not on skip or back. Like `collection.js`, it skips staff.
- `trends.overview` filters both `su_kien` queries with `loai IN ('xem_khong_gian','luu_anh')`. This fixes the KeyError path and is the spec change to `analytics/interest-score`.
- The events stay available for a later "quiz taste" panel.
- *Alternative: weight quiz picks in the score.* The proposal defers this.

### 6. Account result: one row per account
```sql
ket_qua_trac_nghiem (nguoi_dung_id int PRIMARY KEY REFERENCES app_user ON DELETE CASCADE,
                     phong_cach jsonb NOT NULL, goi_y int[] NOT NULL, updated_at timestamptz)
```

- `GET /quiz/me` answers 200 with the stored row, or 204 when there is none.
- `PUT /quiz/me` takes `{cap, chon}`, **re-scores** the answers server-side as in decision 1, and upserts the row. So a saved result can never be invented either.
- Both endpoints use `require(*ROLES)` and `SIGNED_IN`. Suggestions are stored as ids and re-read when the result is fetched. An id that is no longer published is dropped.

### 7. Frontend
- **`src/lib/quiz.js`** keeps `{cap, chon, ket_qua, at}` in `localStorage['d3_trac_nghiem']`, with try/catch.
  - `pendingSave` is a flag. When `session` becomes signed in, it sends the saved `{cap, chon}` to `PUT /quiz/me` once. This follows `collection.js`.
- **`QuizView.vue` `/trac-nghiem`** has three states: start, question and result.
  - **Start** shows the last result if there is one. A signed-in user's saved result comes from `GET /quiz/me` and takes priority over the browser copy.
  - **Question** shows two large photos as `<button>`s, with `alt` from `alt_text` or the caption. It has a "Bỏ qua" link and a "Quay lại" link, and the progress "Câu i/n". Below 600px the photos stack. Keys 1 and 2 choose a photo, and Esc goes back.
  - **Result** shows the styles with percentage bars and the tiles with `SaveHeart`.
  - **"Lưu tất cả"** calls `collection.add` for each tile. It stops on `FULL_MESSAGE`.
  - **"Xem thêm phong cách X"** goes to `/khong-gian#phong_cach=X`.
  - **"Lưu kết quả"** saves directly when signed in. Otherwise it sets `pendingSave` and opens `/dang-nhap?next=/trac-nghiem`.
- **`SpacesView.vue`** needs no new logic: `useBrowse` already reads its filter state from the URL hash (`#phong_cach=X`), so the result links there. (A `?phong_cach=` query was planned first; the hash reuses what exists.)
- **The session watcher in `lib/quiz.js`** runs in a detached `effectScope`. It is started by the quiz page but must outlive it, because the pending result is saved while the visitor is on `/dang-nhap`.
- **Header room:** the page uses a shared `.page-top` class (same offsets as `.pv`). `/uoc-tinh` and `/bo-suu-tap` had their titles under the fixed header and now use it too.
- **Offline (`ai.state === 'off'`)**: show the "cần bản đầy đủ" message.

## Risks / Trade-offs

- **[Few photos, so attempts repeat]** With 40 photos, repeat visitors see similar pairs. → Random seeds, and the pool grows as staff publish. The quiz uses whatever is published, with no config.
- **[A style "wins" partly because its photos are better]** Photo quality biases the picks. → Same-space-type pairing reduces this. It is an accepted limit for a 6-question quiz, and the result text says "phù hợp nhất với bạn" and not a verdict.
- **[Invented pairs]** A visitor can POST their own pairs. → This only changes their own result, and every id must be published. It is documented in decision 1.
- **[Avg of embeddings across very different photos]** If someone picks one photo of each style, the centroid is muddy. → The suggestions are still limited to the top 2 styles, so they stay relevant.
- **[New event type breaks old readers]** `trends.py` is fixed in this change. `discovery.py` already filters. `demo_activity.py` only writes views and saves.

## Migration Plan

- `schema.sql` additions are idempotent:
  - drop and re-add `su_kien_loai_check` with the 3 types;
  - `CREATE TABLE IF NOT EXISTS ket_qua_trac_nghiem`.
- Apply them with `docker compose exec -T db psql -U d3 -d d3 < backend/schema.sql`, then `docker compose up -d --build backend web`.
- **Rollback:** the new table and the event type are additive. Reverting the code leaves harmless rows.
