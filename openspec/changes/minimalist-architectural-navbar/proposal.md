## Why

Redesign the site header navigation to match an ultra-minimalist, unconventional, and high-contrast architectural aesthetic inspired by top design & architecture firms (such as AHL Architects Associates). The current dark navbar lacks distinct architectural character, whitespace balance, and brand identity.

## What Changes

- **Architectural BrandMark**: Replace the old SVG logo with a sleek, interactive 3x3 dot grid mark (red geometric matrix) paired with stacked architectural typography ("d3 studio / architecture & interior").
- **Minimalist Right-aligned Navigation**: Align main navigation links ("Dự án", "D3er", "Tin tức", "Liên hệ") neatly to the right with crisp spacing, active state highlighting in bold accent red, and clean hover indicators.
- **Bilingual Switcher**: Integrate an inline language switcher ("VI | EN") on the far right of the navigation header.
- **Clean Responsive Drawer**: Adapt mobile navigation to retain the ultra-clean light aesthetic with bold typography and smooth transition.

## Capabilities

### New Capabilities
- `navigation/minimalist-navbar`: Ultra-minimalist architectural navbar layout, interactive 3x3 dot mark logo, language switcher, and refined architectural typography.

### Modified Capabilities

## Impact

- `src/components/SiteNav.vue`: Main header component structure, navigation links, language state, responsive mobile drawer.
- `src/components/BrandMark.vue`: Interactive 3x3 red dot matrix logo component.
- `src/css/` / `src/assets/`: Styling updates for light architectural header, typography hierarchy, hover dynamics, and accent color tokens.
