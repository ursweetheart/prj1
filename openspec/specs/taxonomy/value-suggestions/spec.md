# taxonomy/value-suggestions Specification

## Purpose
Let reviewers set a photo's room type and style by typing, with suggestions from the stored taxonomy, and let them propose a missing value that an AI check de-duplicates and describes before the lead architect accepts or rejects it.

## Requirements

### Requirement: Typing Field With Ranked Suggestions
On the review page, a photo's room type and style SHALL be set through a typing field. As the reviewer types, the field SHALL show the best stored value of that dimension as inline completion, and a list of up to 6 matches, compared without accents or case against code, display name and synonyms.

#### Scenario: Inline completion
- **WHEN** a reviewer types "Ja" in the style field and Japandi is the best match
- **THEN** "pandi" appears as grey completion after the cursor, and Tab or the right arrow accepts Japandi

#### Scenario: Accents and synonyms
- **WHEN** a reviewer types "hien" or "modern" in the style field
- **THEN** Hiện đại is offered

#### Scenario: Several matches
- **WHEN** a reviewer types "t" in the style field and Tân cổ điển and Tối giản both match
- **THEN** both are listed, the grey completion shows the first one, and Up / Down and Enter choose another

### Requirement: Match Ranking
Matches SHALL be ordered: display name starts with the typed text, then a synonym starts with it, then the display name contains it. Within each group, values carried by more photos SHALL come first.

#### Scenario: Prefix before contains
- **WHEN** a reviewer types "dien"
- **THEN** a value whose name starts with "dien" is listed before Tân cổ điển, which only contains it

#### Scenario: Usage breaks ties
- **WHEN** two values both start with the typed text and one is carried by 41 photos and the other by 23
- **THEN** the one with 41 photos is listed first and shown as the grey completion

### Requirement: Keyboard and Screen Reader Use
The typing field SHALL work fully by keyboard and SHALL expose its list to assistive technology as a combobox with options. Escape SHALL close the list and keep the typed text, and leaving the field without choosing SHALL restore the photo's saved value.

#### Scenario: Escape and leave
- **WHEN** a reviewer types "xyz", presses Escape, then moves focus away
- **THEN** the list closes and the field shows the photo's saved value again, with nothing saved

### Requirement: Suggest a New Value
When the typed text matches no stored value, the list SHALL offer to suggest it as a new value. Before saving a suggestion, the system SHALL check for a near spelling match locally, then ask the AI whether the word means an existing value, and SHALL offer that existing value instead when either check finds one.

#### Scenario: Typo
- **WHEN** a reviewer suggests "Japandy" for a style
- **THEN** the reviewer is asked "Did you mean Japandi?" without calling the AI, and choosing it sets the photo's style to Japandi

#### Scenario: Same meaning, different words
- **WHEN** a reviewer suggests "Nhật Bắc Âu" and the AI answers that it means Japandi
- **THEN** the reviewer is offered Japandi with the AI's one-line reason, and may still choose to send the suggestion

#### Scenario: Genuinely new
- **WHEN** a reviewer suggests "Mid-century" and neither check finds an existing value
- **THEN** a value suggestion is saved with an AI-drafted description and synonyms, the photo's style becomes `Khac`, and the photo's card shows "Waiting for approval: Mid-century"

#### Scenario: The AI explains the word and checks the photo
- **WHEN** a reviewer suggests "Mid-century" for a photo that looks Indochine
- **THEN** the suggestion stores the AI's closest existing value and how the word differs from it, 3 to 5 recognisable features, and whether this photo shows them; the reviewer sees at once a warning that the photo doesn't seem to match, naming the closer value, and the approver sees the features, the closest value and the photo verdict on the suggestion

#### Scenario: Caption redrafted in the same AI call
- **WHEN** a reviewer suggests "Brutalist" for a photo whose caption describes it as Indochine, and the AI judges that the photo shows Brutalist features
- **THEN** the same AI answer includes a caption and alt text for this photo as Brutalist; the suggestion keeps them with the photo's caption at that moment, the review card offers them unsaved, and the approver's card shows the caption each waiting photo will get; when the AI judges the photo does not match, no caption is drafted

#### Scenario: Accepting writes the drafted caption
- **WHEN** an approver accepts or maps a suggestion, possibly under another name
- **THEN** each moved photo whose caption is unchanged since the suggestion gets the drafted caption and alt text, with the typed word replaced by the final value's name, and the change is written to the review log; a caption a person changed meanwhile is kept

#### Scenario: AI unavailable
- **WHEN** a reviewer suggests a new word while the AI cannot be reached
- **THEN** the suggestion is still saved without a description, and the photo's field becomes "Other"

### Requirement: One Suggestion per Word
A suggestion SHALL be identified by its dimension and its folded text (no accents, lower case, spaces and dashes ignored). Suggesting a word that already has an undecided suggestion SHALL add the photo to it and SHALL NOT call the AI again.

#### Scenario: Two reviewers, same word
- **WHEN** one reviewer suggests "Mid-century" for photo 12 and another suggests "mid century" for photo 30
- **THEN** there is one suggestion that lists photos 12 and 30

### Requirement: Who Can Suggest
Suggesting a value SHALL be open to every role that can edit a photo's tags. AI checks SHALL be rate-limited per user, and anonymous requests SHALL get 401.

#### Scenario: Architect suggests
- **WHEN** an architect suggests a new style
- **THEN** the suggestion is saved, but no value is created until an approver accepts it

#### Scenario: Too many checks
- **WHEN** a user sends more than 10 suggestions that need the AI within a minute
- **THEN** further ones are refused with 429 until the minute passes

### Requirement: Approver Decides Value Suggestions
Lead architects and admins SHALL see undecided value suggestions on the taxonomy suggestions tab, each with its dimension, the photos waiting on it, and the AI's drafted description and synonyms. They SHALL be able to edit the name, description and synonyms, then accept, map the suggestion to an existing value, or reject. Other roles SHALL get 403.

#### Scenario: Accept
- **WHEN** an approver accepts "Mid-century" with an edited description
- **THEN** the value is created in `phong_cach` with that description and synonyms, the change is written to the taxonomy log, and every photo waiting on it whose style is still `Khac` now has style Mid-century and carries its tag

#### Scenario: Photo changed while waiting
- **WHEN** a photo waiting on a suggestion was set to Japandi by someone before the suggestion was accepted
- **THEN** accepting does not change that photo

#### Scenario: Name already taken
- **WHEN** an approver accepts a suggestion whose name gives a code that already exists in the dimension
- **THEN** the server answers 409 and nothing changes

#### Scenario: Map to an existing value
- **WHEN** an approver decides that suggestion "Nhật Bắc Âu" means Japandi and maps it there
- **THEN** no value is created, "Nhật Bắc Âu" is added to Japandi's synonyms, and the waiting photos whose style is still `Khac` get Japandi

#### Scenario: Reject
- **WHEN** an approver rejects a suggestion
- **THEN** no value is created, the waiting photos stay "Other", and the "Waiting for approval" note disappears from their cards
