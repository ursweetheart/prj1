# style-quiz Specification

## Purpose
Lets a visitor who cannot name their taste find it by choosing between photos (UC06, seq-12): a short quiz of photo pairs names the design styles that fit them best and shows published spaces close to what they chose.

## Requirements

### Requirement: Quiz page
The site SHALL offer the quiz at `/trac-nghiem` to everyone, signed in or not. It SHALL be linked from the home search band, from `/khong-gian` and from the footer. Without a backend (the static build) the page SHALL say the quiz is unavailable instead of showing an error.

#### Scenario: Open from the home page
- **WHEN** a visitor follows "Trắc nghiệm phong cách" in the home search band
- **THEN** `/trac-nghiem` opens with a start button and a one-line explanation of what the quiz does

#### Scenario: Static build
- **WHEN** the site runs without a backend and a visitor opens `/trac-nghiem`
- **THEN** the page says the quiz needs the full version of the site and offers a link to `/du-an`

### Requirement: Photo pairs
Each attempt SHALL get 6 questions, or fewer (at least 4) when the photos do not allow 6. Each question is a pair of two published photos from two different styles. Photos SHALL be published spaces whose style is not `Khac`, and only styles with at least 2 such photos take part. No photo SHALL appear twice in an attempt. Styles SHALL be shown as evenly as their photos allow. Where both styles have photos of the same space type, the pair SHALL use that space type.

#### Scenario: A normal attempt
- **WHEN** 40 spaces are published in Indochine, Luxury, Hiện đại and Japandi and a visitor starts the quiz
- **THEN** they get 6 pairs, 12 distinct published photos, every pair has two different styles, and each style is shown 3 times

#### Scenario: Uneven styles
- **WHEN** only Indochine (13 photos) and Japandi (3 photos) take part
- **THEN** the attempt has 3 pairs at most, each Indochine against Japandi, so the quiz is not available

#### Scenario: A style with one photo
- **WHEN** Wabi-sabi has only 1 published photo
- **THEN** Wabi-sabi does not appear in any pair

#### Scenario: Different on each attempt
- **WHEN** a visitor presses "Làm lại"
- **THEN** they get a new set of pairs, not necessarily the same photos as before

### Requirement: Not enough photos
When the eligible photos allow fewer than 4 pairs (for example, only one style takes part), the quiz SHALL NOT start, and the page SHALL say the quiz is not available yet.

#### Scenario: Too few published photos
- **WHEN** only Indochine has published photos
- **THEN** the quiz request answers that the quiz is not available, and the page shows that message instead of pairs

### Requirement: Answering
For each pair the visitor SHALL be able to choose one photo, or skip the pair with "Bỏ qua". The page SHALL show their progress (for example "Câu 3/6"), and SHALL let them go back one question to change their answer. It SHALL work by tap, mouse and keyboard, and each photo SHALL have a text alternative.

#### Scenario: Choose
- **WHEN** a visitor taps the left photo in question 3
- **THEN** question 4 is shown and the progress reads "Câu 4/6"

#### Scenario: Skip every pair
- **WHEN** a visitor skips every pair, or chooses only 1 photo
- **THEN** no result is computed and the page asks them to choose at least 2 photos or try again

### Requirement: Scoring on the server
The result SHALL be computed by the server from the photos shown and the photos chosen, never from scores sent by the client. Each chosen photo SHALL add 1 point to its style. A style's score SHALL be its points divided by how many times it was shown. The 2 highest scoring styles with at least 1 point SHALL be the result, each with its share of the total of all style scores as a percentage.

#### Scenario: A clear winner
- **WHEN** Japandi was shown 3 times and chosen 3 times, Hiện đại shown 3 times and chosen 2, Luxury shown 3 times and chosen 1, and Indochine shown 3 times and never chosen
- **THEN** the result is Japandi (50%) and Hiện đại (33%)

#### Scenario: Only one style chosen
- **WHEN** every chosen photo is Indochine
- **THEN** the result is Indochine alone at 100%

### Requirement: Answers are checked
The server SHALL reject an answer set as invalid (422) and compute nothing when fewer than 2 photos are chosen, a chosen photo is not one of a shown pair, two photos are chosen from one pair, a photo appears in two pairs, or any photo is not a published space with a real style.

#### Scenario: Forged answer
- **WHEN** a request says space 99 was chosen but space 99 was not in any pair it lists
- **THEN** the server answers 422 and computes nothing

#### Scenario: Unpublished photo
- **WHEN** a request lists a draft space in one of its pairs
- **THEN** the server answers 422

### Requirement: Suggested spaces
With the result the server SHALL return up to 8 published spaces of the result's styles, not including any photo shown in the quiz. They SHALL be ordered by how visually close each is to the photos the visitor chose. Each suggestion SHALL carry its style, so the page can show it under the matching style.

#### Scenario: Suggestions follow the choices
- **WHEN** the result is Japandi and Hiện đại
- **THEN** up to 8 published Japandi or Hiện đại spaces that were not in the quiz are returned, closest to the chosen photos first

### Requirement: Result page
The result SHALL name each style with its Vietnamese name and percentage. It SHALL show the suggested spaces as tiles that open the space page, each with the save heart. It SHALL also offer "Lưu tất cả vào bộ sưu tập", "Xem thêm phong cách <tên>" (to `/khong-gian` filtered by that style) and "Làm lại".

#### Scenario: Save all suggestions
- **WHEN** a visitor presses "Lưu tất cả vào bộ sưu tập" on a result with 8 suggestions
- **THEN** the 8 spaces are added to their collection, and the header count goes up by the number that were not already in it

#### Scenario: See more of a style
- **WHEN** a visitor presses "Xem thêm phong cách Japandi"
- **THEN** `/khong-gian` opens with the Japandi style filter already selected

### Requirement: Quiz answers are behaviour signals
Each chosen photo SHALL send a behaviour event `chon_trac_nghiem` for that photo. For a consented session it SHALL be stored with the session id and the photo's taxonomy values at that moment. Without consent only the day's anonymous count SHALL move. Skips and going back SHALL NOT send an event. Staff answering the quiz SHALL NOT send events.

#### Scenario: Consented pick
- **WHEN** a visitor who accepted collection chooses space 21 in a pair
- **THEN** a `chon_trac_nghiem` event with their session id and the `dimension:value` snapshot of space 21 is stored

#### Scenario: Pick without consent
- **WHEN** a visitor who declined chooses a photo
- **THEN** only the day's anonymous `chon_trac_nghiem` count goes up by one

### Requirement: Last result in the browser
The visitor's last result SHALL be kept in their browser. When they come back to `/trac-nghiem`, the page SHALL show that result with "Làm lại" instead of starting a new attempt.

#### Scenario: Come back later
- **WHEN** a visitor finished the quiz, closed the tab and opens `/trac-nghiem` the next day on the same browser
- **THEN** they see their previous result and suggestions, and a "Làm lại" button

### Requirement: Save the result to an account
A signed-in visitor SHALL be able to save their latest result to their account with "Lưu kết quả". An account keeps one result, and saving again replaces it. A visitor who is not signed in SHALL be sent to sign in, and the pending result SHALL be saved as soon as they are signed in. A signed-in visitor opening `/trac-nghiem` on any device SHALL see their saved result. Only the account's owner SHALL be able to read or change it.

#### Scenario: Sign in to save
- **WHEN** an anonymous visitor presses "Lưu kết quả", signs in, and returns
- **THEN** the result is saved to their account and the page says "Đã lưu kết quả"

#### Scenario: Another device
- **WHEN** a visitor saved their result on a laptop and signs in on their phone
- **THEN** `/trac-nghiem` on the phone shows the saved result

#### Scenario: Not signed in
- **WHEN** a request without a signed-in user reads or saves the account's result
- **THEN** the server answers 401

### Requirement: Suggested projects
With the result the server SHALL return up to 3 catalog projects with published photos of the result's styles, ranked by how many of their published photos have those styles and then by how close their best photo is to the photos the visitor chose. Each SHALL carry its slug, name, whether it has a page, the matched style and one photo. With no such project the list SHALL be empty.

#### Scenario: Projects follow the result
- **WHEN** the result is Indochine and Japandi, and two projects have published Indochine photos
- **THEN** those two projects are returned, the one with more Indochine photos first, each with one of its Indochine photos

#### Scenario: Nothing published yet
- **WHEN** no project has a published photo of the result's styles
- **THEN** the result has an empty project list and the suggested spaces are unchanged
