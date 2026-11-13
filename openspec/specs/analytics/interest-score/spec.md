# analytics/interest-score Specification

## Purpose
Turns consented behaviour into an interest score per taxonomy value and a trend against the recent past (QT-06: act-3, seq-4), so the business can see which styles, tones and materials visitors are drawn to and which are rising or falling.

## Requirements

### Requirement: Saves are behaviour signals
Saving a published space with the heart SHALL send a behaviour event `luu_anh`. Under the same consent rule as views, it SHALL be stored with the session id and the space's taxonomy values at that moment for a consented session, and only counted in the day's anonymous total otherwise. Removing a photo from the collection SHALL NOT send an event.

#### Scenario: Consented save
- **WHEN** a visitor who accepted collection saves space 21
- **THEN** a `luu_anh` event with their session id and the `dimension:value` snapshot of space 21 is stored

#### Scenario: Save without consent
- **WHEN** a visitor who declined saves space 21
- **THEN** no per-session event is stored and the anonymous `luu_anh` count for the day goes up by one

### Requirement: Interest score per taxonomy value
For a period, the interest score of a taxonomy value SHALL be views × 1 + saves × 3 + photos sent in a brief × 5, counting each consented view or save event carrying that value and each sent brief photo whose space has that value. Values coded `khac` SHALL be left out. Each value's share SHALL be its score divided by the sum of scores in its dimension.

#### Scenario: Weighted score
- **WHEN** within the period `phong_cach:Wabi_sabi` appears on 10 viewed spaces, 2 saved spaces and 1 photo of a sent brief
- **THEN** its score is 10 + 6 + 5 = 21

#### Scenario: Share
- **WHEN** the style scores in the period are Wabi-sabi 21, Indochine 9 and Khác 5
- **THEN** the shares are 70% and 30%, and Khác is not listed

### Requirement: Trend against the 4-week average
For every value the system SHALL compare the score of the last 7 days with the average weekly score of the 4 weeks before them, giving a change in percent. A value SHALL be "đang tăng" when the last week is at least 1.5 times that average and has at least 5 signals, and "đang giảm" when the last week is at most half of an average that is itself at least 5. A value with no earlier activity and at least 5 signals in the last week SHALL count as "mới nổi".

#### Scenario: Rising
- **WHEN** Wabi-sabi scored 4, 6, 5 and 5 in the 4 weeks before and 12 in the last 7 days
- **THEN** its change is +140% and it is "đang tăng"

#### Scenario: Too little activity
- **WHEN** a value went from an average of 1 to 3 in the last week
- **THEN** it is not marked, because the last week has fewer than 5 signals

### Requirement: Aggregates only
The analytics SHALL only return counts, scores and space ids, never a session id, account or contact data, and SHALL be computed only from consented events, sent briefs and lead counts.

#### Scenario: No session ids
- **WHEN** the overview is requested
- **THEN** the response contains no session id and no personal data
