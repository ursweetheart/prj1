# Proposal

## Why

When the assistant suggests examples, it shows loose photos. A visitor asking for "phòng khách chung cư phong cách Japandi" (a Japandi living room in an apartment) gets a few thumbnails from different projects and has to guess which project fits them. What a client actually chooses a studio by is **a project**: one place where the style, the rooms and the building type all match.

Some projects match more of the request than others. Project A might have Japandi photos of both a living room and a bedroom in an apartment, while project B only has one Japandi bedroom in a villa. The assistant should put A first.

## What Changes

- **The assistant returns example projects instead of loose photos.** The matching photos are grouped by project (the photo folder), and the projects are ranked:
  1. how many of the visitor's collected constraints the project matches (style, room type, building type), where each constraint counts if at least one published photo of the project has it;
  2. the best similarity of its photos to the question;
  3. how many of its photos match.
- **Up to 3 project cards per answer.** Each card has the project name, what matched (e.g. "Japandi · phòng khách · chung cư") and its 1–2 best photos. A card opens the project page on its best photo (`/du-an/<slug>?anh=<file>`) when the project has a page, otherwise that photo's space page (`/khong-gian/<id>`).
- **Both places that show photos today** use the cards:
  - answers from the knowledge base when the visitor gave constraints, which today show 3 photos from text search;
  - answers written from photo descriptions, which today show the photos the AI used. Those photos are grouped by project, keeping the AI's choice.
- Only published photos are ever used, as today.
- The response keeps `images` (the cards' photos, flattened) for compatibility, and adds `projects`.
- Out of scope:
  - Materials and investment level as ranking factors: the chat doesn't extract them from messages today.
  - A project page for projects that exist only in the database: those cards open the space page.

## Capabilities

### New Capabilities

- `assistant-project-results`: how the assistant chooses, ranks and shows example projects in its answers.

### Modified Capabilities

- `assistant-conversations`: "Constraints carry across the conversation" said the collected constraints are used "when choosing example photos". It now says "example projects", ranked by those constraints.

## Impact

- **Backend:**
  - `pipeline/assistant.py`: `respond` builds `projects` for both answer paths.
  - New `pipeline/project_results.py`: candidate search, grouping, ranking. It reuses the SigLIP text embedding (`pipeline.search`) and the `loai_cong_trinh` tags in `space_gia_tri`.
- **Frontend:** `src/components/ChatWidget.vue` renders project cards instead of thumbnails, reading project names and pages through the existing `projectBySlug` / `projectPhotoHref` (read-only use of Tùng's project data).
- **No schema change, no extra AI calls.** One more database query per answer that shows examples.
