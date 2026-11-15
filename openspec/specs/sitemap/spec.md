# sitemap Specification

## Purpose

Tells search engines which public pages exist (seq-6 step 18, roadmap 4.5). The sitemap lists the public pages, projects with published photos and each published photo, and follows publishing and take-downs at once; robots.txt points to it and keeps crawlers out of staff and account pages.

## Requirements

### Requirement: A sitemap of the public site
The site SHALL serve a valid XML sitemap (sitemaps.org 0.9) at `<site>/sitemap.xml` with content type `application/xml`, without sign-in. All addresses SHALL be absolute and built on the configured public site address.

#### Scenario: Absolute addresses
- **WHEN** the public site address is `https://d3studio.vn/`
- **THEN** every `<loc>` starts with `https://d3studio.vn/`

### Requirement: What the sitemap lists
The sitemap SHALL list:
- the public pages: home, `/du-an`, `/khong-gian`, `/uoc-tinh`, `/trac-nghiem`, `/lien-he` and `/ve-chung-toi`;
- `/du-an/<slug>` for each project with at least one published photo;
- `/khong-gian/<id>` for each published photo.

Photo entries SHALL carry `lastmod`, the date of the photo's latest change. Project entries SHALL carry the latest `lastmod` of their published photos.

#### Scenario: Published photo
- **WHEN** photo 812 of project folder `beaumont_lounge` is published
- **THEN** the sitemap lists `<site>/khong-gian/812` and `<site>/du-an/beaumont-lounge`, each with a `lastmod`

### Requirement: Only published content is listed
The sitemap SHALL NOT list:
- photos in draft, waiting for editing or review, or kept internal;
- projects with no published photo;
- staff pages, sign-in, password pages, or shared moodboard links.

#### Scenario: Draft photo
- **WHEN** a photo is in draft
- **THEN** its `/khong-gian/<id>` is not in the sitemap

#### Scenario: Staff pages
- **WHEN** anyone reads the sitemap
- **THEN** no address in it contains `/quan-tri`, `/khach-hang`, `/dang-nhap`, `/dat-mat-khau`, `/quen-mat-khau` or `/bo-suu-tap`

### Requirement: The sitemap follows publishing at once
A publish SHALL appear in the next read of the sitemap, and so SHALL a take-down, a return to draft, or a move to internal. No manual rebuild is needed.

#### Scenario: Take-down
- **WHEN** the lead architect takes a published photo down and the sitemap is read right after
- **THEN** the photo's address is gone, and its project is gone too if it has no other published photo

### Requirement: robots.txt
The site SHALL serve `<site>/robots.txt`. It SHALL allow crawling, point to the sitemap, and disallow `/quan-tri`, `/khach-hang`, `/dang-nhap`, `/dat-mat-khau`, `/quen-mat-khau` and `/bo-suu-tap/xem`.

#### Scenario: Crawler reads robots.txt
- **WHEN** a crawler reads `<site>/robots.txt`
- **THEN** it finds a `Sitemap:` line and a `Disallow:` line for `/quan-tri`
