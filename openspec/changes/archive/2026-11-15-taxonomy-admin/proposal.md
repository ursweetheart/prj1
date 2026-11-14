# Proposal

## Why

The taxonomy is data now (`chieu_phan_loai`, `gia_tri_phan_loai`), but the only screen for it, `/quan-tri/phan-loai`, reviews AI proposals. To add a style, rename a value, add a customer word to a value's synonyms, or merge two values, the lead architect has to use Swagger. seq-15 and roadmap 1.1 call for a taxonomy admin screen, and NFR-13 says the taxonomy can change without a deployment.

There is also a correctness problem in the existing merge. Three dimensions mirror a column of `space`:
- `phong_cach` mirrors `design_style`;
- `khong_gian` mirrors `space_type`;
- `tong_mau` mirrors `palette`.

The merge moves the tag rows but leaves those columns alone. The quiz, the trend snapshots and the AI tag trigger read the columns, so a merged style silently comes back or loses its tags the next time a space is edited. The merge also accepts two values from different dimensions.

## What Changes

- **A "Danh mục" tab on `/quan-tri/phan-loai`** (lead architect, admin), next to the existing "Đề xuất của AI" tab. It shows every dimension with its values. For each value it shows the display name, code, synonyms, and how many spaces and published spaces carry it.
- **Values:**
  - add a value (name, description, synonyms; the code is derived from the name and shown before saving);
  - rename (the code stays the same);
  - edit the description and synonyms;
  - merge into another value of the same dimension, after a warning that names how many spaces and projects are affected and asks for confirmation.
- **Dimensions:**
  - add a dimension by hand (name, one or several values per space, shown to visitors or not);
  - rename;
  - show or hide it for visitors;
  - move it up or down in the filter order.
- **Merge keeps the mirrored columns in step.** Merging in `phong_cach` or `khong_gian` also rewrites `space.design_style` or `space.space_type` from the source code to the target code. `tong_mau` values come from the colour extractor and **cannot** be merged (422). A merge across two dimensions answers 422.
- **New and extended endpoints** (approvers only):
  - `GET /taxonomy/admin`: the tree with usage counts;
  - `POST /taxonomy`: new dimension;
  - `PATCH /taxonomy/{dim_id}`: name, visibility, order;
  - `PATCH /taxonomy/values/{id}`: now also the description and synonyms.
- **Every change is recorded** in a new `nhat_ky_phan_loai` table (who, what, before → after), and is shown as "Gần đây" under the tree.

## Capabilities

### New Capabilities
- `taxonomy/taxonomy-admin`: the staff screen and API for viewing and editing dimensions and values, with usage counts and a change log.

### Modified Capabilities
- `taxonomy/data-driven-taxonomy`: "Value Merge Migrates Labels" now requires both values to be in the same dimension and the mirrored space columns to move with the tags. Derived dimensions (`tong_mau`) cannot be merged. The vector-index refresh step is dropped, because no stored embedding contains labels.

## Impact

- **Backend:**
  - `backend/schema.sql`: new table `nhat_ky_phan_loai`;
  - `backend/api.py`: the new endpoints, the fixed merge, and the extended value patch;
  - new `backend/pipeline/taxonomy_admin.py`;
  - new `backend/tests/test_taxonomy_admin.py`.
- **Frontend:**
  - `src/api.js`: the new calls;
  - `src/views/TaxonomyView.vue`: becomes two tabs; the candidate review moves into `src/components/TaxonomyCandidates.vue` unchanged;
  - new `src/components/TaxonomyTree.vue`.
- **Out of scope:**
  - deleting a value or dimension (merging covers values; a dimension can be hidden);
  - picture examples for a value (`anh_minh_hoa`);
  - editing which dimension the AI classifier fills;
  - undo.
