# collections/saved-collection Specification

## Purpose
Lets a visitor keep the spaces they like, with a note per photo, without needing an account, and keep them across devices once signed in. A saved collection is the input of the design brief sent to an architect.

## Requirements

### Requirement: Save a photo with a heart
Every space tile on `/khong-gian` and the space page `/khong-gian/<id>` SHALL show a heart button. Activating it SHALL add the space to the visitor's collection, or remove it if it is already there, without leaving the page. The button SHALL show its state (filled when saved) and have a label naming the action ("Lưu vào bộ sưu tập" / "Bỏ khỏi bộ sưu tập").

#### Scenario: Save from the search page
- **WHEN** a visitor presses the heart on a tile on `/khong-gian`
- **THEN** the heart becomes filled, the tile does not open, and the collection count in the header goes up by one

#### Scenario: Unsave from the space page
- **WHEN** a visitor presses the filled heart on `/khong-gian/21`
- **THEN** space 21 is removed from the collection and the heart is empty again

### Requirement: Collection without an account
Without signing in, the collection SHALL be kept only in the visitor's browser and SHALL survive reloads and new tabs on the same browser. Nothing about it SHALL be sent to the server until the visitor signs in or sends a brief.

#### Scenario: Reload
- **WHEN** an anonymous visitor saves 3 spaces and reloads the site
- **THEN** the collection still has those 3 spaces, and no request was made to the collection endpoints

### Requirement: Collection kept in the account
A signed-in visitor's collection SHALL be stored on the server, one collection per account, so it is the same on every device where they sign in. Saving, removing and editing a note SHALL be saved to the account.

#### Scenario: Another device
- **WHEN** a signed-in visitor saves space 21 on their laptop and then signs in on their phone
- **THEN** the collection on the phone contains space 21

### Requirement: Keep the browser collection when signing in
When a visitor signs up or signs in (email or Google/Facebook) while the browser holds a collection, the browser items SHALL be merged into the account collection: spaces already in the account keep their note unless it is empty, new spaces are added, and the browser collection is then cleared.

#### Scenario: Sign up keeps the photos
- **WHEN** an anonymous visitor with 3 saved spaces creates an account
- **THEN** their account collection has those 3 spaces with their notes, and the browser no longer holds a separate collection

#### Scenario: Same space on both sides
- **WHEN** the browser has space 21 with note "thích màu gỗ" and the account has space 21 with no note
- **THEN** after sign-in the account has space 21 once, with note "thích màu gỗ"

### Requirement: Limits
A collection SHALL hold at most 60 spaces and each note at most 300 characters. Only published spaces SHALL be saved. A space that is unpublished later SHALL disappear from the collection view.

#### Scenario: Full collection
- **WHEN** a visitor with 60 saved spaces presses another heart
- **THEN** the space is not added and they see "Bộ sưu tập đã đủ 60 ảnh"

### Requirement: Collection page
`/bo-suu-tap` SHALL list the saved spaces (photo, space type, project name, link to the space page), each with an editable note and a remove action, and a "Gửi cho kiến trúc sư" action when it holds at least one space. An empty collection SHALL say how to save photos and link to `/khong-gian`. An anonymous visitor SHALL see an invitation to sign up so the collection is not lost.

#### Scenario: Anonymous visitor with photos
- **WHEN** an anonymous visitor with 2 saved spaces opens `/bo-suu-tap`
- **THEN** they see the 2 photos with note fields, "Gửi cho kiến trúc sư", and a "Đăng ký để giữ bộ sưu tập" link to sign up

#### Scenario: Empty
- **WHEN** a visitor with no saved spaces opens `/bo-suu-tap`
- **THEN** they see a short explanation and a link to `/khong-gian`

### Requirement: Header link with count
The site header SHALL show a "Bộ sưu tập" link to `/bo-suu-tap` with the number of saved spaces when it is above zero. It SHALL appear only when the AI backend answers, like the "Không gian" item.

#### Scenario: Count
- **WHEN** a visitor has 4 saved spaces
- **THEN** the header shows "Bộ sưu tập (4)"

### Requirement: Read-only shared view
A collection sent as a brief SHALL be viewable at `/bo-suu-tap/xem/<ma>` by anyone with the link, read-only: photos, notes and the summary, without the sender's name or contact data. The code SHALL be random and unguessable. An unknown code SHALL show "Không tìm thấy bộ sưu tập".

#### Scenario: Consultant opens the link
- **WHEN** a consultant opens the share link from a brief email
- **THEN** they see the photos with the visitor's notes and the summary, and no phone number or email

#### Scenario: Wrong code
- **WHEN** someone opens `/bo-suu-tap/xem/abc`
- **THEN** they see "Không tìm thấy bộ sưu tập"
