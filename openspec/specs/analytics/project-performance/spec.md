# analytics/project-performance Specification

## Purpose

Shows how each published project does after publishing (BFD 5.4, act-1 "theo dõi hiệu quả sau 30 ngày"): its views, saves and leads, which photos draw attention, and, for projects that are not being seen, concrete changes to make.

## Requirements

### Requirement: Who sees project results
Project results SHALL be visible to architects, the lead architect, admin and sales. Visitors and content editors SHALL get 403, and anonymous requests 401. The results SHALL contain only counts, never a session id, account or contact.

#### Scenario: Visitor
- **WHEN** a visitor requests the project results
- **THEN** the server answers 403

### Requirement: One row per published project
For a period of the last 30 or 90 days, `/quan-tri/hieu-qua` SHALL list every project (photo folder) with at least one published photo, with:
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

### Requirement: Leads per project
A lead SHALL count for a project when its context names that project's page, when its context names one of the project's photos, or when its brief sent one of the project's photos. A lead SHALL count once per project, and a lead touching two projects SHALL count once for each.

#### Scenario: Brief with photos of two projects
- **WHEN** a brief sends two photos of project A and one of project B
- **THEN** A and B each count that lead once

### Requirement: Attention status after 30 days
A project whose first photo was published at least 30 days ago SHALL be "Cần xem lại" when its views in the last 30 days are below half the median views of all such projects, and "Ổn" otherwise. A project published less than 30 days ago SHALL be "Đang theo dõi" with the number of days left. With fewer than 3 projects old enough to compare, no project SHALL be marked "Cần xem lại".

#### Scenario: Below half the median
- **WHEN** projects published over 30 days ago had 40, 30, 20 and 6 views in the last 30 days
- **THEN** the one with 6 views is "Cần xem lại" (the median is 25, half is 12.5) and the others are "Ổn"

#### Scenario: Too new
- **WHEN** a project was published 10 days ago
- **THEN** it is "Đang theo dõi, còn 20 ngày" whatever its views

### Requirement: Photo detail
Expanding a project SHALL show each of its published photos with its views and saves in the period, most viewed first, and mark the photos that had no views.

#### Scenario: A photo nobody looked at
- **WHEN** one of a project's 5 photos had no views in the period while the others had some
- **THEN** it is listed last and marked "chưa ai xem"

### Requirement: Suggestions for a project
The detail SHALL list the suggestions that apply, each linking to where it is fixed on `/quan-tri`:
- no "Loại công trình" or "Mức đầu tư" tag on any photo;
- photos whose style is "Khác" or has a confidence below 0.5;
- fewer published photos than half the median of all projects;
- photos with no views while the project has some;
- captions under half the project's median caption length.

#### Scenario: Missing manual tags
- **WHEN** none of a project's photos has a "Loại công trình" tag
- **THEN** the suggestions say that filters by project type miss it, with a link to tag the project on `/quan-tri`

#### Scenario: Nothing to suggest
- **WHEN** a project has all tags, clear styles and normal captions, and every photo was viewed
- **THEN** the detail says there is nothing to fix

### Requirement: My projects
An architect SHALL be able to show only the projects with at least one photo they uploaded.

#### Scenario: Only mine
- **WHEN** an architect who uploaded photos of one project ticks "Chỉ dự án tôi tải lên"
- **THEN** only that project is listed

### Requirement: Demo data is labelled
While simulated demo activity exists, the page SHALL show "Đang hiển thị cả dữ liệu mô phỏng", as the trend dashboard does.

#### Scenario: Demo loaded
- **WHEN** demo sessions exist and a sales user opens the page
- **THEN** the banner is shown above the list

### Requirement: Usable on a phone and by keyboard
The page SHALL be usable at 360px without sideways page scroll, and every row SHALL expand and collapse by keyboard.

#### Scenario: Phone
- **WHEN** an architect opens `/quan-tri/hieu-qua` on a 360px screen
- **THEN** every project's name, status, views, saves and leads are readable without scrolling sideways
