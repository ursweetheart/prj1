# Proposal

## Why

The search diagrams explain results; the code only lists them:
- **seq-2 steps 9-10:** similar spaces should come with a reason built from the labels they share.
- **seq-8 steps 4-6 and 13:** photo search should first check that the upload is an interior, refuse politely otherwise, and tell the visitor "your photo looks like style X, tone Y".
- **seq-11 steps 3-4 and 11-12:** description search should pull the room type and style out of the sentence as hard filters, give a reason per result, and suggest rewording when the matches are weak.
- **seq-10 and BFD 1.1-1.2:** project filtering should count results per value, suggest which filter to loosen when nothing matches, and sort.

## What Changes

- **Similar spaces** (`GET /spaces/{id}/similar`): each result carries `ly_do`, its shared labels by name, for example "Cùng phong cách Japandi · Cùng tông Ấm". Cards show it.
- **Photo search** (`POST /search/image`):
  - it checks that the upload is an interior;
  - otherwise it answers with a polite refusal and no results;
  - for an interior it returns the photo's likely style and tone with a confidence (from its nearest library photos), plus the results with reasons.
- **Description search** (`GET /search`):
  - room-type and style words in the sentence (by name or synonym, accents ignored) become hard filters;
  - the rest is embedded;
  - each result carries the labels it matched;
  - when the best match is weak, the answer carries a rewording hint.
- **Project filter API** (`GET /projects/filter`):
  - published projects filtered by style, building type, area range and investment level;
  - counts per value given the other filters;
  - a "loosen this filter" suggestion when nothing matches;
  - sorting by newest, area or most viewed.

  A ready `ProjectFilter.vue` component goes with it. The user decided Tùng wires it into `/du-an`.
- **Space explorer sorting** (BFD 1.2): newest, most viewed, or by style, inside the facet panel.
- **Search notes on `/khong-gian`:** a small `SearchNote.vue` shows the photo traits, the refusal, the filters taken from the sentence and the rewording hint. It is one line in Tùng's `SpacesView.vue`, approved by the user.
- **BREAKING (API only):**
  - `/search` and `/search/image` return `{ket_qua, ...}` instead of a bare list;
  - `src/api.js` keeps returning the list (with the extra fields attached), so callers don't change.

## Capabilities

### New Capabilities
- `search-explanations`: reasons on similar and description results, photo traits and the non-interior refusal, constraints taken from a description, and the rewording hint.
- `project-filter`: filtering, counting, loosening suggestions and sorting of published projects.

### Modified Capabilities
- `space-explorer`: sorting of the explorer's results, and the search note.

## Impact

- **Backend:**
  - `pipeline/search.py`: reasons, query constraints, traits, interior check;
  - `api.py`: response shapes, `GET /projects/filter`, `sort` on `GET /spaces`.
- **Frontend:**
  - `src/api.js`: `toCard` passes `ly_do`, the search wrappers, a `lastSearch` store;
  - `SpaceTile.vue`: reason line;
  - new `SearchNote.vue` and `ProjectFilter.vue`;
  - `FacetPanel.vue` / `useBrowse.js`: sorting;
  - one line in `SpacesView.vue`.
- **No new model or Gemini calls:** everything uses the stored labels and the local SigLIP2 embedder.
