## MODIFIED Requirements

### Requirement: Interest score per taxonomy value
For a period, the interest score of a taxonomy value SHALL be views × 1 + saves × 3 + photos sent in a brief × 5, counting each consented view or save event carrying that value and each sent brief photo whose space has that value. Other behaviour events (such as quiz answers, `chon_trac_nghiem`) SHALL NOT be counted in the score, the totals or the trend. Values coded `khac` SHALL be left out. Each value's share SHALL be its score divided by the sum of scores in its dimension.

#### Scenario: Weighted score
- **WHEN** within the period `phong_cach:Wabi_sabi` appears on 10 viewed spaces, 2 saved spaces and 1 photo of a sent brief
- **THEN** its score is 10 + 6 + 5 = 21

#### Scenario: Share
- **WHEN** the style scores in the period are Wabi-sabi 21, Indochine 9 and Khác 5
- **THEN** the shares are 70% and 30%, and Khác is not listed

#### Scenario: Quiz answers are not scored
- **WHEN** within the period `phong_cach:Japandi` appears on 4 quiz answer events and nothing else
- **THEN** Japandi's score, view count and save count are all 0
