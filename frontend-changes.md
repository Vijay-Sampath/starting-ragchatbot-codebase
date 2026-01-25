# Frontend Changes

This document describes the frontend improvements made to the Course Materials Assistant.

---

## Dark/Light Theme Toggle

### Overview
Added a theme toggle button that allows users to switch between dark and light themes with smooth transitions and persistent preferences.

### Files Modified

#### 1. `frontend/index.html`
- Added a theme toggle button with sun and moon SVG icons positioned at the top-right of the page
- Button includes proper accessibility attributes (`aria-label`, `title`)

**Changes:**
```html
<!-- Theme Toggle Button -->
<button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme" title="Toggle theme">
    <svg class="sun-icon">...</svg>
    <svg class="moon-icon">...</svg>
</button>
```

#### 2. `frontend/style.css`
Added approximately 120 lines of new CSS:

**Light Theme Variables (`[data-theme="light"]`):**
- `--background: #f8fafc` - Light gray background
- `--surface: #ffffff` - White surface color
- `--surface-hover: #f1f5f9` - Light hover state
- `--text-primary: #1e293b` - Dark text for readability
- `--text-secondary: #64748b` - Medium gray for secondary text
- `--border-color: #e2e8f0` - Light border color
- `--assistant-message: #f1f5f9` - Light assistant message background
- Adjusted colors for links, code blocks, and status messages

**Theme Toggle Button Styles (`.theme-toggle`):**
- Fixed position at top-right corner
- Circular button (44px diameter)
- Hover effects with scale transform
- Focus ring for accessibility
- Responsive sizing for mobile

**Icon Visibility Logic:**
- Dark theme: Shows moon icon (click to switch to light)
- Light theme: Shows sun icon (click to switch to dark)

**Smooth Transitions:**
- Added 0.3s ease transitions for background-color, border-color, color, and box-shadow on all major elements

#### 3. `frontend/script.js`
Added theme management functionality:

**New Functions:**
- `initializeTheme()` - Loads saved theme from localStorage on page load, defaults to dark
- `toggleTheme()` - Switches between dark and light themes, saves preference to localStorage

**New Event Listener:**
- Theme toggle button click event to call `toggleTheme()`

**New DOM Element:**
- Added `themeToggle` to the list of tracked DOM elements

### Features Implemented

1. **Toggle Button Design**
   - Icon-based design (sun/moon icons)
   - Positioned in top-right corner
   - Smooth hover and active animations
   - Keyboard accessible (focusable, has focus ring)

2. **Light Theme Colors**
   - Light background (#f8fafc)
   - Dark text for contrast (#1e293b)
   - Adjusted primary, secondary, and accent colors
   - Proper border and surface colors
   - Good accessibility contrast ratios

3. **JavaScript Functionality**
   - Theme toggles on button click
   - Preference saved to localStorage
   - Preference persists across page reloads
   - Defaults to dark theme for new users

4. **Implementation Details**
   - Uses CSS custom properties (CSS variables)
   - Theme applied via `data-theme` attribute on `<body>`
   - All existing elements styled correctly in both themes
   - Smooth 0.3s transitions between themes

### Browser Support
- Works in all modern browsers (Chrome, Firefox, Safari, Edge)
- localStorage used for persistence (supported in all modern browsers)
- CSS transitions provide smooth visual feedback

### Accessibility
- Button has `aria-label` for screen readers
- Visible focus ring for keyboard navigation
- Good color contrast in both themes
- Button is keyboard navigable (focusable)

---

## Code Quality Tools Implementation

### Overview

Added essential code quality tools for automatic code formatting and linting consistency throughout the frontend codebase. These tools ensure consistent code style and catch common issues early in development.

### New Files Created

#### Configuration Files

| File | Purpose |
|------|---------|
| `frontend/package.json` | npm package configuration with dev dependencies and scripts |
| `frontend/.prettierrc` | Prettier configuration for code formatting |
| `frontend/.prettierignore` | Files to exclude from Prettier formatting |
| `frontend/.eslintrc.json` | ESLint configuration for JavaScript linting |
| `frontend/.eslintignore` | Files to exclude from ESLint |
| `frontend/.stylelintrc.json` | Stylelint configuration for CSS linting |
| `frontend/.stylelintignore` | Files to exclude from Stylelint |
| `frontend/quality-check.sh` | Shell script to run all quality checks |

### Tools Added

#### 1. Prettier (Code Formatting)

**Version:** ^3.2.0

Prettier automatically formats JavaScript, CSS, HTML, and JSON files for consistent code style.

**Configuration highlights:**
- 4-space indentation
- Single quotes for JavaScript
- Semicolons required
- 100-character print width
- ES5 trailing commas

#### 2. ESLint (JavaScript Linting)

**Version:** ^8.56.0

ESLint catches JavaScript errors and enforces coding standards.

**Key rules enabled:**
- `eqeqeq`: Require strict equality (`===`)
- `curly`: Require curly braces for all control statements
- `prefer-const`: Prefer `const` over `let` when possible
- `no-var`: Disallow `var` declarations
- `no-console`: Warn on console usage (allows `log`, `warn`, `error`)

**Additional packages:**
- `eslint-config-prettier`: Disables ESLint rules that conflict with Prettier

#### 3. Stylelint (CSS Linting)

**Version:** ^16.2.0

Stylelint catches CSS errors and enforces styling standards.

**Configuration highlights:**
- Extends `stylelint-config-standard`
- Allows vendor prefixes (needed for webkit compatibility)
- Allows camelCase ID selectors (existing codebase pattern)
- Requires quotes around font family names

### NPM Scripts

Run these commands from the `frontend/` directory:

| Command | Description |
|---------|-------------|
| `npm run format` | Format all files with Prettier |
| `npm run format:check` | Check formatting without modifying files |
| `npm run lint:js` | Run ESLint on JavaScript files |
| `npm run lint:js:fix` | Run ESLint and auto-fix issues |
| `npm run lint:css` | Run Stylelint on CSS files |
| `npm run lint:css:fix` | Run Stylelint and auto-fix issues |
| `npm run lint` | Run both ESLint and Stylelint |
| `npm run lint:fix` | Run both linters with auto-fix |
| `npm run quality` | Run formatting check and all linters |
| `npm run quality:fix` | Format and fix all linting issues |

### Shell Script

The `quality-check.sh` script provides a convenient way to run all quality checks:

```bash
# Check only (default)
./quality-check.sh

# Auto-fix issues
./quality-check.sh --fix

# Show help
./quality-check.sh --help
```

### Usage

#### Initial Setup

```bash
cd frontend
npm install
```

#### Development Workflow

Before committing changes, run the quality check:

```bash
# Option 1: Using npm scripts
npm run quality:fix

# Option 2: Using the shell script
./quality-check.sh --fix
```

#### CI/CD Integration

For continuous integration, use the check-only mode:

```bash
npm run quality
```

This will exit with a non-zero status if any issues are found.

### Dependencies

All development dependencies (installed via `npm install`):

```json
{
  "prettier": "^3.2.0",
  "eslint": "^8.56.0",
  "eslint-config-prettier": "^9.1.0",
  "stylelint": "^16.2.0",
  "stylelint-config-standard": "^36.0.0"
}
```

### Notes

- The existing codebase has been formatted to comply with the new quality standards
- All quality checks currently pass
- The tools are configured to be permissive of existing patterns (e.g., ID selectors in CSS)
- Run `npm run quality:fix` whenever you make changes to ensure consistency
