# project-catalog Specification

## Purpose

Gives the studio one list of projects shared by the site, the AI backend and the dashboards, so every photo belongs to a known project with a name, a page when it has one, and the details visitors ask about.

## Requirements

### Requirement: Project record
The backend SHALL keep one record per project with: slug, name, type (`loai`), year, short description, display order, whether it has a page on the site, area in m², bedrooms, build time, investment level (a `muc_dau_tu` taxonomy value) and design concept text. Slugs SHALL be unique and match `[a-z0-9-]{1,60}`.

#### Scenario: A site project
- **WHEN** the catalog holds `beaumont-lounge`
- **THEN** its record has name "Beaumont Lounge", type `lounge`, a page on the site, and empty project details until staff fill them

### Requirement: Sync from the site's project list
A backend command SHALL add every project of the site's project list to the catalog and update its name, type, year, short description and order. It SHALL NOT change the area, bedrooms, build time, investment level or concept text. It SHALL NOT delete a project; a project gone from the site list SHALL be marked as having no page.

#### Scenario: Re-run after a rename on the site
- **GIVEN** the lead architect entered 120 m² for `luxury-apartment`
- **WHEN** the site renames it "Luxury Apartment II" and the sync runs again
- **THEN** the name is updated and the area is still 120 m²

#### Scenario: Removed from the site
- **WHEN** a project is removed from the site list and the sync runs
- **THEN** its record stays, marked as having no page, and its photos keep their project

### Requirement: Site photos matched to stored spaces
The sync SHALL link each site photo to the stored space showing the same picture, so no photo is analysed twice. A space SHALL belong to at most one project and match at most one site photo; it SHALL record the site file name. A site photo with no match SHALL stay unlinked unless new-photo ingest is requested.

#### Scenario: Same photo, other folder
- **GIVEN** space `hanjadin/behance_img_3.jpg` shows the same picture as site photo `hanjadin-apartment/02.jpg`
- **WHEN** the sync runs
- **THEN** that space belongs to `hanjadin-apartment` with site file `02.jpg`, and no new space is created

#### Scenario: Not a match
- **WHEN** the closest stored space to a site photo is only a similar room, not the same picture
- **THEN** the site photo stays unlinked and is reported as unmatched

### Requirement: Ingest only unmatched photos
With new-photo ingest requested, the sync SHALL turn each unmatched site photo into a draft space of its project, at most a given number per run. It SHALL NOT publish anything and SHALL NOT touch photos already linked.

#### Scenario: Limited ingest
- **GIVEN** 40 site photos are unmatched
- **WHEN** the sync runs with ingest and a limit of 10
- **THEN** 10 new draft spaces are created in their projects and 30 photos stay unmatched

### Requirement: Sync is previewable and recorded
The sync SHALL offer a dry run that reports, per project, how many site photos matched, how many are unmatched and which spaces would be linked, without writing. Every link it writes SHALL be logged with the similarity score, and a second run with nothing new SHALL change nothing.

#### Scenario: Dry run
- **WHEN** staff run the sync as a dry run
- **THEN** the report lists matches and unmatched photos per project and the database is unchanged

### Requirement: Folder-only projects
A photo folder whose spaces belong to no site project SHALL have its own project record, with the folder as name and no page. A space uploaded at `/quan-tri` into a new folder SHALL belong to that folder's project.

#### Scenario: Upload into a new folder
- **WHEN** an architect uploads photos into a new folder `nha_anh_tuan`
- **THEN** a project with no page exists for it and the photos belong to it

### Requirement: Project list API
`GET /projects` SHALL return, in display order, each project's slug, name, type, year, short description, whether it has a page, number of published photos and its first published photo. Visitors SHALL get only projects with at least one published photo; staff SHALL get all projects with their draft photo count as well.

#### Scenario: Visitor
- **GIVEN** 64 projects, 12 of them with published photos
- **WHEN** a visitor calls `GET /projects`
- **THEN** 12 projects are returned

### Requirement: Project detail API
`GET /projects/{slug}` SHALL return the project record and its published spaces, in the site's photo order when they match site photos and by file name otherwise, each with its site file name when it has one. Staff SHALL also get draft spaces. An unknown slug, or a project with no published photo for a visitor, SHALL get 404.

#### Scenario: Site photo order
- **WHEN** a visitor opens the detail of a project whose published spaces match site photos `03.jpg` and `01.jpg`
- **THEN** the spaces come in the order `01.jpg`, `03.jpg`, each naming its site file

#### Scenario: Unknown project
- **WHEN** anyone calls `GET /projects/khong-co`
- **THEN** the API answers 404

### Requirement: Edit project details
The lead architect and admin SHALL be able to set a project's area, bedrooms, build time, investment level and concept text with `PUT /projects/{slug}`. Area and bedrooms SHALL be positive numbers, the investment level SHALL be a stored `muc_dau_tu` value, and the concept text SHALL be at most 4,000 characters. Others SHALL get 403. Each change SHALL be logged with who made it and the old and new values.

#### Scenario: Valid edit
- **WHEN** the lead architect sets 85 m², 2 bedrooms and investment level `700tr_1500tr` on `apartment-in-grey`
- **THEN** the project shows those values and the log records the change

#### Scenario: Bad value
- **WHEN** the lead architect sends an investment level that is not in the taxonomy
- **THEN** the API answers 422 and nothing changes

#### Scenario: Architect
- **WHEN** an architect sends the edit
- **THEN** the API answers 403
