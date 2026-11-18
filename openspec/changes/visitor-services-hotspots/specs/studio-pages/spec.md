## ADDED Requirements

### Requirement: Services page
The site SHALL have a page at `/dich-vu` that lists the service packages in use, each with its title and description and an anchor made from its title. Below the list it SHALL show the studio's work process and links to the cost estimate, the style quiz and the contact page. Visitors SHALL see only services in use; a sample description SHALL carry the "Thông tin mẫu" mark instead of the raw marker text. Without a backend the page SHALL show the sample packages from the studio data, marked as samples.

#### Scenario: Footer link
- **WHEN** a visitor follows "Dịch vụ và quy trình" in the footer
- **THEN** `/dich-vu` shows the packages in use, the 5 steps and the three links, and the footer link is no longer dead

#### Scenario: Draft service
- **WHEN** a service entry is a draft or switched off
- **THEN** it is not on `/dich-vu` and `GET /services` does not return it

#### Scenario: Anchor from a hotspot
- **WHEN** a visitor opens `/dich-vu#dich_vu_thiet_ke_phong_khach`
- **THEN** the page scrolls to "Dịch vụ thiết kế phòng khách" once the list has loaded
