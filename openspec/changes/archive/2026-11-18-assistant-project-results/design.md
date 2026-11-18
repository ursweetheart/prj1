# Design

## Context

See proposal.md for why and `specs/assistant-project-results/spec.md` for the behaviour.

`pipeline/assistant.py` → `respond` fills `out["images"]` in two places:
- **Photo answers:** when the knowledge base doesn't know, `retrieve_photos` (transcript embeddings, `k=4`, published only) feeds `answer_from_photos`. Its `hits` are the photos the AI said it used.
- **Knowledge-base answers with constraints:** `by_text(q, space_type, 3, published_only=True)`, i.e. SigLIP text → image search, at most `PER_PROJECT` per project.

Other relevant facts:
- **Collected constraints:** `req` (merged across the conversation) has `design_style`, `space_type`, `project_type` (a `loai_cong_trinh` value code) and `area_m2`. Materials aren't extracted.
- **Project of a photo:** the first segment of `relative_path`. `project_stats.py` uses `split_part(relative_path, '/', 1)`, and the frontend `slugOf` turns `_` into `-`. Building type is a person-set tag in `space_gia_tri` (dimension `loai_cong_trinh`).
- **Frontend:** `ChatWidget.vue` renders `t.images` as thumbnails linking to `/khong-gian/<id>`. `src/lib/projectSpaces.js` has `slugOf` and `projectPhotoHref`, and `src/data/projects.js` has `projectBySlug` (the static project pages).

## Goals / Non-Goals

**Goals:**
- One ranking function, testable without the AI, used by both answer paths.
- No extra AI call; one SQL query for the knowledge-base path.

**Non-Goals:**
- Changing which answer text the assistant writes, or the photo-answer retrieval itself.
- Project pages for database-only projects.
- Ranking by materials or investment level.

## Decisions

**1. `pipeline/project_results.py`: `rank(photos, req, k=3, per=2) -> list[dict]`.**
Input: candidate photos `{id, relative_path, space_type, design_style, loai_cong_trinh: [codes], sim}`, best first.
1. Group by project folder.
2. For each project, compute the **matched constraints**: the set of `req` keys among `design_style`, `space_type`, `project_type` that are set and that at least one photo in the group has.
3. Sort projects by `(len(matched) desc, max sim desc, count desc)`.
4. Within a project, pick its photos by `(constraints the photo itself matches desc, sim desc)`, up to `per`.

Each project is returned as `{folder, khop: [{chieu, ma, ten}], so_anh_khop, anh: [photo]}`, with `ten` taken from `taxonomy.labelled()` so the card can print names.
*Alternative:* score by summed similarity. Rejected because a project with many mediocre photos would beat one that matches the request exactly.

**2. Knowledge-base path: a wider candidate query.**
`candidates(text, limit=60)`: the SigLIP text embedding as `by_text` does it, over published spaces only, with `1 - (embedding <=> v)` as `sim`. Each photo's `loai_cong_trinh` codes come from `space_gia_tri` in the same query. Without a per-project cap, so a project's spread of rooms counts. Then `rank(..., req)`. This replaces the `by_text(q, ..., 3)` call. The room filter is no longer a hard filter, because room type is a ranking factor.

**3. Photo-answer path: keep the AI's photos.**
The photos are `photos["hits"]` in the order used. Their `loai_cong_trinh` codes come from one query, and the function is called as `rank(hits, req, k=3, per=2)` with `sim` = their transcript cosine. Projects are ordered by the first used photo, as the spec requires: this path sorts by first-use order instead of the constraint ranking, because the answer text refers to those photos in that order.

**4. Response.**
`out["projects"]` = ranked projects; `out["images"]` = their photos flattened (cards order), so older clients and `assistant-topic-guard` expectations ("no images") keep working. The small-talk and handoff paths return `projects: []`.

**5. `ChatWidget.vue` project card.**
- **Name:** `projectBySlug(slugOf(folder))?.name`, else the folder with `_` → space.
- **Matched line:** `khop` names joined by " · ", omitted when empty.
- **Photos:** up to two thumbnails.
- **Link:** `projectPhotoHref(best.relative_path)` when `projectBySlug` finds the slug, else `/khong-gian/<best.id>`.
- The whole card is one link with an `aria-label` ("Dự án <name>, khớp …"), and closes the chat like today's thumbnails.

## Risks / Trade-offs

- **Projects with few published photos rank low on "count".** That's only the last tie-breaker; constraints and similarity come first.
- **Building type depends on staff tagging projects.** Untagged projects never match `project_type`. → Acceptable, since staff tag per project on `/quan-tri`. The matched line simply omits it.
- **Folder ≠ static project page slug for some folders,** e.g. old folders like `wallnut`. → The fallback opens the space page.
- **60 candidates is a fixed window.** With ~150 photos it covers about 40% of the library; revisit when the library grows.

## Migration Plan

Deploy backend and frontend together. There's no data change. **Rollback:** revert; `images` stayed in the response, so an old frontend still works with the new backend.
