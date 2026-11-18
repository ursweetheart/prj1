## MODIFIED Requirements

### Requirement: Constraints carry across the conversation
The project type, space type, area and style a visitor mentions SHALL be collected across the conversation. A newer value SHALL replace an older one. Each answer SHALL use the collected constraints, not only those in the current message, when choosing and ranking example projects (capability `assistant-project-results`). A lead created from the chat SHALL store the collected constraints as its request.

#### Scenario: Area said earlier
- **WHEN** a visitor first writes "chung cư 70m2" and later "phong cách wabi-sabi giá bao nhiêu"
- **THEN** the price lead stores project type chung cư, area 70 m² and style Wabi-sabi

#### Scenario: Visitor changes their mind
- **WHEN** a visitor said "chung cư" and later says "à không, nhà phố"
- **THEN** the collected project type is nhà phố

#### Scenario: Earlier style ranks the projects
- **WHEN** a visitor said "Japandi" earlier and now asks "cho mình xem phòng khách"
- **THEN** projects with Japandi living rooms are ranked above living rooms in other styles
