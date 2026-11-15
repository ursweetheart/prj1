# studio-pages Specification

## Purpose

The public pages that say who D3 Studio is and how to reach it ("Về chúng tôi" `/ve-chung-toi`, "Liên hệ" `/lien-he`), which the header, the footer and the home CTA link to. They show the studio's details from one place, and they never let a sample phone, email or address act as a real one.

## Requirements

### Requirement: Contact page
`/lien-he` SHALL show:
- the consultation form;
- the studio's phone, email and Zalo in a section reachable as `/lien-he#zalo`;
- the address and opening hours in a section reachable as `/lien-he#ban-do`, with a link that opens the address in a map;
- links to the cost estimate and the style quiz.

A lead sent from this page SHALL record the page `/lien-he` with no project.

#### Scenario: Sending the form
- **WHEN** a visitor fills in name and phone on `/lien-he` and sends
- **THEN** a "form" lead is stored with the page `/lien-he`, and the visitor sees the form's confirmation

#### Scenario: Footer link to Zalo
- **WHEN** a visitor clicks "Nhắn Zalo" in the footer
- **THEN** `/lien-he` opens scrolled to the Zalo section, fully visible below the header, on a 360px phone and on a 1280px screen

### Requirement: About page
`/ve-chung-toi` SHALL say what D3 Studio does and where, present the team members by name and role, outline how a project runs in short steps, show the number of projects on the site, and link to the projects and the contact page.

#### Scenario: Visitor opens the page
- **WHEN** a visitor opens "Về chúng tôi" from the header
- **THEN** they see the introduction, the team, the steps, the project count matching `/du-an`, and links to "Xem dự án" and "Liên hệ"

### Requirement: Studio details from one source, samples marked
Both pages SHALL read the studio's details from one place. A detail that has not been confirmed as real SHALL be shown with a visible "Thông tin mẫu" mark. A sample phone number, email address or Zalo SHALL be shown as plain text, never as a link that calls, mails or opens a chat. A sample address SHALL have no map link. Once a detail is confirmed, it SHALL appear without the mark and as a working link.

#### Scenario: Sample phone
- **WHEN** the phone number is still a sample
- **THEN** it is shown with "Thông tin mẫu" and is not a `tel:` link

#### Scenario: Confirmed phone
- **WHEN** the real phone number is filled in and confirmed
- **THEN** it is shown without the mark as a `tel:` link, and the Zalo link opens a chat with that number

### Requirement: Usable on a phone and by keyboard
Both pages SHALL start below the fixed header, have no sideways scroll at 360px, set a page title, and have every link and form field reachable by keyboard.

#### Scenario: Phone
- **WHEN** a visitor opens `/ve-chung-toi` or `/lien-he` on a 360px screen
- **THEN** the page heading is visible below the header and nothing scrolls sideways
