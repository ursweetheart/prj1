## Purpose

Defines the layout, branding dot-grid logo, typography, navigation links, bilingual language toggle, and responsive drawer for the minimalist architectural site header.

## ADDED Requirements

### Requirement: Minimalist Architectural Header Layout
The header SHALL render an ultra-minimalist, high-contrast architectural layout featuring clean line dividers, wide margin spacing, and right-aligned navigation items.

#### Scenario: Desktop view rendering
- **WHEN** a user opens any page on a desktop viewport
- **THEN** the header displays the 3x3 dot matrix brand mark on the far left and right-aligned navigation links with ample negative space.

### Requirement: Interactive 3x3 Red Dot Matrix Brand Logo
The brand logo SHALL render a 3x3 grid of red dots alongside stacked architectural typography ("d3 studio") with interactive hover feedback.

#### Scenario: Hovering logo
- **WHEN** a user hovers over the 3x3 dot matrix logo
- **THEN** the red dots exhibit a subtle scale/opacity reaction and highlight the studio brand label.

### Requirement: Right-Aligned Navigation Links and Active State
The navigation links SHALL include "Dự án", "D3er", "Tin tức", "Liên hệ", with the current active page rendered in bold accent red (`#C01919`).

#### Scenario: Active route indication
- **WHEN** the user navigates to the "Dự án" page
- **THEN** the "Dự án" navigation link is rendered in bold accent red while inactive links display in neutral text color.

### Requirement: Integrated Language Switcher
The navigation header SHALL include an inline language switcher ("VI | EN") on the far right.

#### Scenario: Toggling language switcher
- **WHEN** the user clicks "EN" on the language switcher
- **THEN** the active language highlights "EN" in bold red and updates the interface locale preference.
