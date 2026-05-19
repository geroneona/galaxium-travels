# IBM Carbon Design System Integration

This document describes the IBM Carbon Design System integration in the Galaxium Travels frontend application.

## Overview

The application now supports IBM Carbon Design themes alongside the existing custom space-themed design. Users can switch between different Carbon themes using the theme switcher in the header.

## Features

### Theme Options

The application supports four IBM Carbon themes:

1. **White** - Light theme with white background
2. **Gray 10 (g10)** - Light theme with subtle gray background
3. **Gray 90 (g90)** - Dark theme with deep gray background (default)
4. **Gray 100 (g100)** - Darkest theme with black background

### Theme Persistence

- Selected theme is saved to `localStorage`
- Theme preference persists across browser sessions
- Default theme is Gray 90 (g90) for a dark, modern look

## Implementation Details

### Dependencies

```json
{
  "@carbon/react": "^1.x.x",
  "@carbon/styles": "^1.x.x"
}
```

### File Structure

```
src/
├── theme/
│   └── carbonTheme.ts          # Theme configuration and types
├── hooks/
│   └── useTheme.tsx            # Theme context and hook
├── components/
│   └── common/
│       └── ThemeSwitcher.tsx   # Theme selector component
└── main.tsx                    # Carbon styles import
```

### Key Components

#### 1. Theme Configuration (`theme/carbonTheme.ts`)
Defines available themes and their metadata.

#### 2. Theme Provider (`hooks/useTheme.tsx`)
- React Context for theme state management
- Handles theme persistence to localStorage
- Applies theme to document element via `data-carbon-theme` attribute

#### 3. Theme Switcher (`components/common/ThemeSwitcher.tsx`)
- Dropdown component using Carbon's `Dropdown`
- Allows users to select and switch themes
- Located in the application header

### Usage

#### Using the Theme Hook

```tsx
import { useTheme } from './hooks/useTheme';

function MyComponent() {
  const { theme, setTheme } = useTheme();
  
  return (
    <div>
      <p>Current theme: {theme}</p>
      <button onClick={() => setTheme('g100')}>
        Switch to Dark Theme
      </button>
    </div>
  );
}
```

#### Using Carbon Components

```tsx
import { Button, Dropdown } from '@carbon/react';

function MyComponent() {
  return (
    <div>
      <Button>Carbon Button</Button>
      <Dropdown
        id="my-dropdown"
        titleText="Select option"
        items={[]}
      />
    </div>
  );
}
```

## Styling Integration

### CSS Architecture

The application uses a hybrid approach:

1. **Carbon Styles** - Base design system styles
2. **Tailwind CSS** - Utility classes for custom styling
3. **Custom CSS** - Space-themed overrides and animations

### Theme-Specific Styles

```css
/* Dark themes maintain space theme */
[data-carbon-theme='g90'] body,
[data-carbon-theme='g100'] body {
  @apply bg-space-dark text-star-white;
}

/* Light themes use standard backgrounds */
[data-carbon-theme='white'] body,
[data-carbon-theme='g10'] body {
  @apply bg-gray-50 text-gray-900;
}
```

## Best Practices

1. **Use Carbon Components** - Prefer Carbon components for UI consistency
2. **Theme-Aware Styling** - Use CSS custom properties that adapt to themes
3. **Accessibility** - Carbon components include built-in accessibility features
4. **Performance** - Theme changes are instant with no page reload

## Future Enhancements

- [ ] Add custom Carbon theme with Galaxium branding
- [ ] Implement theme-specific color palettes
- [ ] Add more Carbon components (DataTable, Modal, etc.)
- [ ] Create theme preview before switching
- [ ] Add system theme detection (light/dark mode)

## Resources

- [IBM Carbon Design System](https://carbondesignsystem.com/)
- [Carbon React Components](https://react.carbondesignsystem.com/)
- [Carbon Themes](https://carbondesignsystem.com/guidelines/themes/overview)

## Made with Bob