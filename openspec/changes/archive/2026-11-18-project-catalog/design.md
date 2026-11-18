# Design

## Context

- **Site:**
  - `src/data/projects.js` (Tùng's file) lists 64 projects, one line each: `{ slug, loai, name }`, with optional `year` and `brief`.
  - The photos are in `src/assets/projects/<slug>/NN.jpg` (626 files).
  - A project with no photo folder isn't shown.
- **Backend:**
  - **Photos:** 154 spaces in 10 folders under `image_d3/`, which use Behance file names (`behance_img_N.jpg`). Every space has a SigLIP2 image embedding (`space.embedding`, 768-d, normalised).
  - **Project = folder:** "project" means the first segment of `relative_path`, in `project_stats.py`, `project_results.py`, the `/projects/{folder}/spaces` route and the review screen's "tag a project".
  - **Leads:** a lead from a project page stores `ngu_canh.du_an = <slug>`, and `project_stats` compares it with the folder name after replacing `-` with `_`.
- **Container:** the backend image copies `backend/` only. `src/` isn't mounted, so `ingest_projects.py` (which reads `../src/assets/projects`) can't run in Docker today.
- **Who owns what:** see proposal.md (Why) for motivation. Tùng owns `/du-an`, the project page and `projects.js`. This change only reads them.

## Goals / Non-Goals

**Goals:**
- **One project per space:** every space belongs to exactly one catalog project, without re-analysing photos that are already stored.
- **Project details:** the project details from UC02 are stored and editable.
- **Shared source:** project performance, the assistant and the quiz name projects from the catalog.

**Non-Goals:**
- **Moving files:** stored photos are not moved or renamed. `relative_path` stays as it is, so URLs, logs and caches keep working.
- **Visitor pages:** no change to visitor pages. The static GitHub Pages build keeps working from `projects.js`.
- **Admin pages:** no project create or delete screen. Projects come from the site list or from a folder.

## Decisions

### 1. Project membership is a column, not the folder name
Spaces gain two columns:
- `du_an_slug text REFERENCES du_an(slug) ON UPDATE CASCADE`;
- `anh_trang text`, the site file name, for example `02.jpg`.

Every query that grouped by `split_part(relative_path,'/',1)` groups by `du_an_slug` instead.

*Alternative considered: rename the legacy folders to the slug convention and rename the files to match the site.* The folders hold more photos than the site does (30 vs 16 for Hanjadin) and their names don't line up file by file. Moving files would also mean rewriting `relative_path` in every log and event. A column gives the same answer with no file moves.

### 2. Match by image embedding, mutual best, high threshold
- **Embedding:** the sync embeds each site photo with the existing `VisionEmbedder` on CPU (no API calls) and compares it with all stored space embeddings.
- **Match rule:** a pair matches when each is the other's nearest neighbour and the cosine similarity is ≥ 0.95. The site photos are re-exported copies of the same renders, so true pairs should score about 0.98 or more, while two different rooms of one project rarely pass 0.9.
- **Recording:** the score is written to `nhat_ky_du_an` with each link, and the dry run prints the 10 closest non-matches above 0.85, so the threshold can be checked before writing.

*Alternative considered: perceptual hash (`imagehash`).* It's a new dependency, and it breaks when the site copy was cropped or re-graded. The embedder is already installed and loaded by the processor.

### 3. Leftover photos of a matched folder follow the folder's majority
- **Majority rule:** after matching, a still-unassigned space joins the project that most of its folder's matched spaces went to. This covers Behance photos of a project that the site didn't use.
- **No match:** a folder with no matched space becomes a folder-only project. Its slug is the folder lower-cased with `_` turned into `-`, plus `-thu-muc` if that slug is already taken; its name is the folder and `co_trang` is false.
- **New uploads:** the upload path (`processor` → `store.save_records`) assigns new spaces the same way, with an `INSERT … ON CONFLICT DO NOTHING` for the folder's project.

### 4. Reading `projects.js` without running it
`projects.js` imports a Vite virtual module, so Node can't import it as it is.
- **Parser:** the sync uses a small regex parser over the `PROJECTS = [ … ]` block, reading single-quoted `key: 'value'` pairs and numeric `year`. It's marked `shortcut: single-line object literals only; switch to a JSON export if projects.js grows nested fields`.
- **Has a page:** a project has a page (`co_trang`) only when it is listed *and* `src/assets/projects/<slug>/` has images, the same filter the site applies.
- **Docker access:** `docker-compose.yml` mounts `./src/data` and `./src/assets/projects` read-only at `/src/...`. That path matches `Path(__file__).parent.parent / "src"` inside `/app`, so the old ingest path also works in Docker.

### 5. Ingest of unmatched photos reuses the existing ingest
`ingest_projects.py`'s copy-and-process loop moves into the sync behind `--ingest --limit N`. A new space keeps the slug-folder convention (`<slug with _>/<file>`, as `project-space-sync` specifies) and gets `du_an_slug` and `anh_trang` set at insert. `ingest_projects.py` stays as a thin wrapper that calls the sync with `--ingest`, so the documented command keeps working.

### 6. Site fields vs staff fields
The sync writes only `ten`, `loai`, `nam`, `mo_ta_ngan`, `thu_tu` and `co_trang`.

The staff fields are `dien_tich_m2`, `so_phong_ngu`, `thoi_gian_thi_cong`, `muc_dau_tu` and `thuyet_minh`. They are written only by `PUT /projects/{slug}`, which:
- is open to the lead architect and admin, as with prices and taxonomy;
- validates `muc_dau_tu` against the stored taxonomy values;
- logs to `nhat_ky_du_an` with `truoc` / `sau`.

### 7. APIs stay small and reuse the space fields
- **`GET /projects`:** one SQL query with `count(*) FILTER (WHERE review_status='published')` and the first published photo, ordered by `thu_tu NULLS LAST, ten`.
- **`GET /projects/{slug}`:** the record plus spaces with the existing `FIELDS`, ordered by `anh_trang COLLATE "C" NULLS LAST, relative_path COLLATE "C"`.
- **`GET /projects/{folder}/spaces`:** unchanged. The project page still calls it.
- **Rate limits:** the public reads use the same `limit()` dependency as the other public reads.

### 8. Consumers
- **`project_stats`:** group by `du_an_slug` and add the project name. Leads match on `ngu_canh->>'du_an' = du_an_slug`, with no `-`/`_` replace. The review-screen link carries the project's folder for each space, which is unchanged on that page.
- **`project_results`:** group by `du_an_slug`. A card carries `slug`, `ten` and `co_trang`, so a card opens `/du-an/<slug>?anh=<anh_trang>` only when the project has a page and the photo has a site file.
- **`quiz`:** after choosing spaces, rank projects by the number of published photos in the result's styles, then by their best photo's distance to the mean of the chosen photos (the vector `suggest` already computes), and keep the top 3.
- **`weekly_report`:** names come from the catalog.

## Risks / Trade-offs

- **[A wrong match links a photo to the wrong project]** → mutual best match, a 0.95 threshold, a dry run that shows borderline pairs, and a log of every link with its score. A wrong link is fixed by clearing `du_an_slug` and re-running. The sync never overwrites an existing link.
- **[Legacy folders mix photos of two site projects (for example `Indochine` vs `indochine-apartment` / `indochine-chinoiserie-villa`)]** → per-photo matching decides first. The majority rule only places leftovers, and the dry run lists per folder where its photos went.
- **[`projects.js` changes shape]** → the parser fails loudly when it finds no projects or a line it can't read, and never writes a partial list.
- **[The CPU embedding run is slow]** → 626 images in batches of 16. It is a one-off, and later runs embed only new site photos. Embeddings of site photos are cached by file path and modification time in the log, so a re-run skips unchanged files.
- **[An in-flight change (`assistant-project-results`, task 3.1) expects `folder` on cards]** → keep `folder` in the payload alongside `slug` until that frontend task lands.

## Migration Plan

1. **Schema:** apply the additive schema (`du_an`, `nhat_ky_du_an`, the two `space` columns). The backend starts fine with an empty catalog: consumers fall back to the folder for spaces with no project until step 3 runs.
2. **Preview:** `docker compose exec backend python sync_projects.py --dry-run`, then check the matches and the borderline pairs.
3. **Write:** `sync_projects.py`, which creates the projects, links matched spaces and creates the folder-only projects.
4. **Optional:** `sync_projects.py --ingest --limit 10`, once per batch, when Gemini quota allows.
5. **Rollback:** `UPDATE space SET du_an_slug = NULL, anh_trang = NULL` restores the folder behaviour. The catalog rows can stay.

## Open Questions

- **Threshold:** the exact match threshold (0.95) is confirmed by the dry run on real data. If true pairs score lower, lower it there, without changing the specs or tasks.
