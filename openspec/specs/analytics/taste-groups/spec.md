# analytics/taste-groups Specification

## Purpose
TBD - created by archiving change tracking-pipeline. Update Purpose after archive.

## Requirements

### Requirement: Nightly clustering of sessions into taste groups
After storing the day's scores, the nightly run SHALL group the consented, non-abnormal sessions of the last 30 processed days by the design attributes they engaged with (act-3 "Phân cụm phiên, phát hiện nhóm thị hiếu mới"):
- Only sessions with at least 3 events carrying design attributes SHALL take part.
- The run SHALL try between 2 and 6 groups and keep the number that separates the sessions best.
- With fewer than 10 such sessions, no grouping SHALL be made, and the run SHALL record that there was too little data.

#### Scenario: Enough sessions
- **WHEN** 40 sessions qualify, one half mostly viewing Wabi-sabi wood interiors and the other mostly Indochine
- **THEN** the run stores at least two groups, one led by `phong_cach:Wabi_sabi` and one by `phong_cach:Indochine`

#### Scenario: Too little data
- **WHEN** only 6 sessions qualify
- **THEN** no group is stored and the dashboard says there is not enough data for taste groups

### Requirement: What a group shows
Each stored group SHALL have:
- its share of the qualifying sessions;
- its 3 defining values, those most over-represented in the group compared with all qualifying sessions, excluding `khac` values;
- the run date.

A group SHALL hold no session id.

#### Scenario: Defining values
- **WHEN** a group's sessions view `vat_lieu:go_oc_cho` 4 times as often as sessions overall
- **THEN** `vat_lieu:go_oc_cho` is among its defining values

### Requirement: New taste groups are flagged
A group SHALL be flagged "mới" when its 2 strongest defining values, taken together, did not lead any group in the runs of the previous 28 days. A new group SHALL also appear among the trend alerts of that run.

#### Scenario: New pairing appears
- **WHEN** no earlier group in 28 days was led by Japandi with `mau_sac:xanh_reu`, and today's run finds one
- **THEN** that group is marked "mới" and listed in the trend alerts as a new taste group
