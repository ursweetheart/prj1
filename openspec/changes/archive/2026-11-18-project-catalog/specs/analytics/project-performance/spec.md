# Spec Delta

## MODIFIED Requirements

### Requirement: One row per published project
For a period of the last 30 or 90 days, `/quan-tri/hieu-qua` SHALL list every catalog project (see `project-catalog`) with at least one published photo, under its project name, with:
- its number of published photos;
- the date its first photo was published;
- consented views and saves of its published photos in the period;
- its save rate (saves / views);
- the number of distinct leads it brought in the period;
- its status.

The list SHALL be ordered with "Cần xem lại" first, then by views.

#### Scenario: Counts
- **WHEN** in the last 30 days a project's published photos were viewed 12 times and saved 3 times by consenting visitors
- **THEN** its row shows 12 views, 3 saves and a save rate of 25%

#### Scenario: Named by the catalog
- **WHEN** the spaces of folder `hanjadin` are matched to the site project `hanjadin-apartment`
- **THEN** one row "Hanjadin Apartment" is listed, not a row `hanjadin`

### Requirement: Leads per project
A lead SHALL count for a project when its context names that project's page (`/du-an/<slug>` or the project's slug), when its context names one of the project's photos, or when its brief sent one of the project's photos. A lead SHALL count once per project, and a lead touching two projects SHALL count once for each.

#### Scenario: Brief with photos of two projects
- **WHEN** a brief sends two photos of project A and one of project B
- **THEN** A and B each count that lead once

#### Scenario: Lead from a project page
- **WHEN** a visitor sends the contact form on `/du-an/hanjadin-apartment`, whose photos are stored in folder `hanjadin`
- **THEN** the lead counts for Hanjadin Apartment
