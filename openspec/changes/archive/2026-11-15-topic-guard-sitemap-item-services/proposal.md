# Proposal

## Why

Three small pieces of the design are still missing, and none of them needs Tùng's pages:
- **seq-3 step 15.** The assistant has no list of topics it must not discuss. Today only a fixed money and promise pattern is checked, and only on answers written from photos.
- **seq-6 step 18 and roadmap 4.5.** Published photos are not announced to search engines. There is no `sitemap.xml` and no `robots.txt`.
- **The rest of roadmap 1.9.** Detected sofas and beds point to a service package, but hand-placed hotspots linked to an item point nowhere.

These are the last items buildable before the fixing phase, so they ship together as one change.

## What Changes

- **Forbidden topics.** Content staff, the lead architect and admin keep a list of topics. Each topic has a name, its keywords and an on/off switch. The list is edited in a new tab of `/quan-tri/tri-thuc`.
  - The check runs on both the visitor's question and the draft answer, whether the answer came from the knowledge base or from photos.
  - On a hit, the answer is replaced by a handoff to a person and a handoff lead is created. The message gives no hint of which topic was hit.
  - The hit is recorded on the message, so staff see it in the conversation detail.
  - It is not logged as a knowledge gap.
- **Sitemap.**
  - `GET /sitemap.xml` is built from the database on each request, so a publish or a take-down shows up at once. It lists:
    - the public pages;
    - the project pages that have at least one published photo;
    - each published photo's `/khong-gian/<id>`.
  - nginx serves it at `/prj1/sitemap.xml`.
  - A static `public/robots.txt` points to it and keeps search engines out of `/quan-tri`, `/khach-hang` and the account pages.
- **Items linked to service packages.**
  - An item in the library may point to one service entry of the knowledge base (`kind = service`).
  - A hotspot linked to that item carries the service in the space's public data, the same way a detected sofa does. The item's service takes precedence over the label mapping.
  - The visitor's hotspot card stays name-only: Tùng removed the service line from it (`b6c469b`), and showing it again is his call.
  - Visitors see only services that are in use (`dang_dung`).
  - The service is picked on `/quan-tri/mon-do` and in the hotspot editor's item form.

## Capabilities

### New Capabilities
- `assistant-topic-guard`: the forbidden-topic list, who manages it, how the assistant checks questions and answers against it, and what visitors and staff see on a hit.
- `sitemap`: the public `sitemap.xml` and `robots.txt`, covering what is listed, what is never listed, and how they follow publishing.

### Modified Capabilities
- `hotspot-items`: items gain an optional link to a service package, which each linked hotspot carries in the space's public data.

## Impact

- **Backend:**
  - `schema.sql` gains a new table `chu_de_cam`, plus the columns `tin_nhan.chu_de_cam` and `mon_do.dich_vu_id`.
  - New module `pipeline/topic_guard.py`.
  - `pipeline/assistant.py` changes in `respond()` and `with_services()`.
  - `pipeline/items.py` gains a field and a check on it.
  - `pipeline/conversations.py` stores the hit and shows it to staff.
  - `api.py` gains `/forbidden-topics` CRUD and `GET /sitemap.xml`.
  - New tests.
- **Frontend (all files are ours):**
  - `KnowledgeView.vue` gains a "Chủ đề cấm" tab.
  - `ItemsView.vue` and `HotspotEditor.vue` gain a service picker.
  - `ConversationsView.vue` shows the hit.
  - New `public/robots.txt`.
  - `nginx.conf` gains one location.
- **Not touched:** Tùng's files, which are `App.vue`, the home and project pages, `src/data/projects.js`, `/dich-vu`, `vite.config.js` and the router entries for his pages. `HotspotImage.vue` and `SpaceView.vue` are left alone, so the card stays name-only.
