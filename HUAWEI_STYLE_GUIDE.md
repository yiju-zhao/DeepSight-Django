# HUAWEI Global Design System Style Guide

> Comprehensive design system analysis and style guide based on HUAWEI Global website

## Table of Contents

1. [Overview](#overview)
2. [Color Palette](#color-palette)
3. [Typography](#typography)
4. [Spacing System](#spacing-system)
5. [Component Styles](#component-styles)
6. [Shadows & Elevation](#shadows--elevation)
7. [Animations & Transitions](#animations--transitions)
8. [Border Radius](#border-radius)
9. [Opacity & Transparency](#opacity--transparency)
10. [Layout System](#layout-system)
11. [CSS Variables Reference](#css-variables-reference)
12. [Example Components](#example-components)

---

## Overview

### Design Philosophy

The HUAWEI design system embodies a **modern minimalist** approach with the following core principles:

- **Minimalism**: Generous white space and clean typography create breathing room
- **Strong Contrast**: Bold black/white contrast with strategic red accents
- **Smooth Interactions**: Consistent 0.3s-0.6s transitions throughout the interface
- **Responsive First**: Mobile, tablet, and desktop variations for all components
- **Component-Based Architecture**: Reusable, modular design patterns
- **Brand Consistency**: HUAWEI red (#CE0E2D) used sparingly as a powerful accent
- **Clear Hierarchy**: Systematic type scale from 12px to 40px
- **Accessibility Focus**: Strong color contrast, visible hover states, and clear focus indicators

### Technical Stack

- **No Framework Dependencies**: Custom CSS with component-based architecture
- **Modern CSS Features**: CSS Custom Properties (CSS Variables), Flexbox, Grid
- **BEM-like Naming**: Structured class naming convention
- **Responsive Breakpoints**: Mobile-first approach with 3 main breakpoints
- **Icon System**: Custom SVG icon font (`svgicons`)

---

## Color Palette

### Primary Colors

The foundation of the HUAWEI visual identity:

| Color Name | Hex | RGB | Usage |
|------------|-----|-----|-------|
| **Black** | `#000000` | `rgb(0, 0, 0)` | Primary text, buttons, high-contrast elements |
| **White** | `#FFFFFF` | `rgb(255, 255, 255)` | Background, text on dark surfaces |
| **HUAWEI Red** | `#CE0E2D` | `rgb(206, 14, 45)` | Brand accent, CTAs, highlights |
| **Red Hover** | `#A20A22` | `rgb(162, 10, 34)` | Hover state for red elements |

### Grayscale Palette

Comprehensive grayscale system for text, borders, and backgrounds:

| Color Name | Hex | RGB | Usage |
|------------|-----|-----|-------|
| **Dark Text** | `#1E1E1E` | `rgb(30, 30, 30)` | Primary body text |
| **Dark Element** | `#24272A` | - | Dark UI components |
| **Medium Gray** | `#666666` | `rgb(102, 102, 102)` | Secondary text |
| **Icon Gray** | `#7F7F7F` | `rgb(127, 127, 127)` | Icons, muted elements |
| **Muted Text** | `#7B7B7B` | - | Tertiary text |
| **Light Gray** | `#B1B1B1` | `rgb(178, 178, 178)` | Disabled states, placeholders |
| **Border Gray** | `#E3E3E3` | `rgb(227, 227, 227)` | Dividers, borders |
| **Background Gray** | `#F5F5F5` | `rgb(245, 245, 245)` | Surface backgrounds |
| **Separator Gray** | `#F7F7F7` | `rgb(247, 247, 247)` | Subtle separators |

### Functional Colors

| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| **Link Blue** | `#2788D9` | `rgb(39, 136, 217)` | Hyperlinks, interactive elements |

### Transparency Values

Pre-defined transparency levels for consistent layering:

| Name | RGBA | Usage |
|------|------|-------|
| **White 30%** | `rgba(255, 255, 255, 0.3)` | Transparent white borders on dark backgrounds |
| **Black 10%** | `rgba(0, 0, 0, 0.1)` | Very subtle shadows, borders |
| **Black 30%** | `rgba(0, 0, 0, 0.3)` | Light borders, inactive borders |
| **Black 60%** | `rgba(0, 0, 0, 0.6)` | Modal overlays, dialogs |
| **Black 80%** | `rgba(0, 0, 0, 0.8)` | Tooltips, high-contrast overlays |

### Color Usage Guidelines

**Do's:**
- Use black and white as primary colors for maximum readability
- Reserve HUAWEI red for important CTAs and brand moments
- Use grayscale for hierarchy without introducing unnecessary color
- Maintain 4.5:1 contrast ratio for text (WCAG AA)

**Don'ts:**
- Don't overuse the red accent (dilutes brand impact)
- Avoid pure gray text on gray backgrounds
- Don't use low-contrast color combinations

---

## Typography

### Font Families

The system uses **system font stack** for optimal performance:

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Icon Font:**
```css
font-family: "svgicons"; /* Custom SVG icon font */
```

### Font Size Scale

A comprehensive, responsive type scale across all breakpoints:

#### Desktop (≥1080px)

| Name | Size | Line Height | Usage |
|------|------|-------------|-------|
| **Hero Title Large** | `40px` | `1.25` | Main hero headlines |
| **Hero Title** | `36px` | `1.25` | Secondary hero headlines |
| **Display** | `32px` | `1.25` | Section headers |
| **H1** | `28px` | `1.321` | Page titles |
| **H2** | `24px` | `1.25` | Section titles |
| **H3** | `20px` | `1.5` | Subsection titles |
| **Body Large** | `16px` | `1.6` | Primary body text |
| **Body Small** | `14px` | `1.6` | Secondary text |
| **Button** | `13px` | `1.2307` | Button labels |
| **Caption** | `12px` | `1.5` | Captions, metadata |
| **Icon** | `10px` - `22px` | - | Icon sizes |

#### Tablet (768px - 1079px)

| Name | Size | Line Height | Usage |
|------|------|-------------|-------|
| **Hero Title** | `36px` | `1.25` | Hero headlines |
| **H1** | `24px` | `1.25` | Page titles |
| **H2** | `20px` | `1.5` | Section titles |
| **Body** | `16px` / `14px` | `1.6` | Body text |
| **Caption** | `12px` | `1.5` | Small text |

#### Mobile (≤767px)

| Name | Size | Line Height | Usage |
|------|------|-------------|-------|
| **Hero Title** | `24px` - `22px` | `1.25` | Hero headlines |
| **H1** | `16px` | `1.5` | Page titles |
| **H2** | `14px` | `1.5` | Section titles |
| **Body** | `14px` / `12px` | `1.6` | Body text |
| **Button** | `12px` / `10px` | `1.2` | Button labels |

### Font Weights

| Weight | Value | Usage |
|--------|-------|-------|
| **Extra Bold** | `800` | Major hero text, strong emphasis |
| **Bold** | `700` | Headings, primary CTAs, active states |
| **Semi-Bold** | `600` | Subheadings, medium emphasis |
| **Medium** | `500` | Navigation items, buttons, emphasized body text |
| **Regular** | `400` | Default body text, standard UI elements |

### Letter Spacing

Most text uses default letter spacing with these exceptions:

- **Navigation Items**: `0.3px` - Improves readability in small text
- **Uppercase Text**: `0.5px` - Opens up tight letterforms
- **Buttons**: Default to `0px`

### Typography Combinations

**Hero Section:**
```css
/* Main headline */
font-size: 40px;
font-weight: 800;
line-height: 1.25;
color: #000000;

/* Supporting text */
font-size: 16px;
font-weight: 400;
line-height: 1.6;
color: #666666;
```

**Card Component:**
```css
/* Card title */
font-size: 20px;
font-weight: 700;
line-height: 1.5;
color: #1E1E1E;

/* Card body */
font-size: 14px;
font-weight: 400;
line-height: 1.6;
color: #666666;
```

**Button Text:**
```css
font-size: 13px;
font-weight: 500;
line-height: 1.2307;
letter-spacing: 0px;
text-transform: none;
```

### Responsive Typography Pattern

```css
/* Mobile-first approach */
.hero-title {
  font-size: 24px;
  line-height: 1.25;
  font-weight: 800;
}

/* Tablet */
@media (min-width: 768px) {
  .hero-title {
    font-size: 36px;
  }
}

/* Desktop */
@media (min-width: 1080px) {
  .hero-title {
    font-size: 40px;
  }
}
```

---

## Spacing System

### CSS Custom Properties

The system uses CSS variables for consistent, responsive spacing:

```css
:root {
  /* Section spacing */
  --pc-margin-top: 80px;
  --pc-margin-bottom: 80px;
  --pad-margin-top: 80px;
  --pad-margin-bottom: 80px;
  --mob-margin-top: 40px;
  --mob-margin-bottom: 40px;

  /* Component spacing */
  --padding-top: [value];
  --padding-bottom: [value];
  --padding-top-xs: [value];
  --padding-bottom-xs: [value];
}
```

### Spacing Scale

A consistent spacing scale based on increments:

| Name | Value | Usage |
|------|-------|-------|
| **XXS** | `4px` | Minimal gaps, tight spacing |
| **XS** | `8px` | Small component padding |
| **SM** | `12px` | Button padding, small gaps |
| **MD** | `16px` | Standard component spacing |
| **LG** | `24px` | Medium component padding |
| **XL** | `32px` | Large component spacing |
| **2XL** | `40px` | Section spacing (mobile) |
| **3XL** | `48px` | Large section padding |
| **4XL** | `60px` | Extra-large spacing |
| **5XL** | `80px` | Section spacing (desktop) |

### Container Padding

Responsive horizontal padding for page containers:

#### Desktop (≥1600px)
```css
padding-left: 80px;
padding-right: 80px;
```

#### Desktop (<1600px)
```css
padding-left: 40px;
padding-right: 40px;
```

#### Tablet (768px - 1079px)
```css
padding-left: 40px;
padding-right: 40px;
```

#### Mobile (≤767px)
```css
padding-left: 16px;
padding-right: 16px;
/* or */
padding-left: 20px;
padding-right: 20px;
```

### Section Spacing

Vertical spacing between major page sections:

```css
/* Desktop & Tablet */
.section {
  margin-top: var(--pc-margin-top); /* 80px */
  margin-bottom: var(--pc-margin-bottom); /* 80px */
}

/* Mobile */
@media (max-width: 767px) {
  .section {
    margin-top: var(--mob-margin-top); /* 40px */
    margin-bottom: var(--mob-margin-bottom); /* 40px */
  }
}
```

### Component Padding Patterns

**Large Components:**
```css
padding: 48px 80px; /* Desktop */
padding: 50px 40px; /* Tablet */
```

**Medium Components:**
```css
padding: 32px;
padding: 40px;
```

**Small Components:**
```css
padding: 16px;
padding: 24px;
```

**Buttons:**
```css
/* Default */
padding: 9px 16px 8px;

/* Medium */
padding: 8px 15px 7px;

/* Large */
padding: 17px 31px 15px;

/* Small */
padding: 10px 17px;
padding: 10px 20px;
```

### Grid System & Gutters

Uses **negative margin technique** for gutters:

```css
/* Container */
.grid-container {
  margin-left: -4px;
  margin-right: -4px;
  /* or */
  margin-left: -14px;
  margin-right: -14px;
}

/* Grid items */
.grid-item {
  padding-left: 4px;
  padding-right: 4px;
  /* or */
  padding-left: 14px;
  padding-right: 14px;
}
```

### Gap Spacing (Flexbox/Grid)

Common gap values for modern layouts:

```css
gap: 12px;  /* Small gaps */
gap: 16px;  /* Default gaps */
gap: 24px;  /* Medium gaps */
gap: 32px;  /* Large gaps */
```

---

## Component Styles

### Buttons

HUAWEI's button system features 7 distinct variants with consistent hover states.

#### Button Variants

##### 1. Black Button (Primary)

**Default State:**
```css
.btn-black {
  background-color: #000000;
  color: #ffffff;
  border: 0;
  padding: 9px 16px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2307;
  transition: opacity 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-black:hover {
  opacity: 0.8;
}
```

##### 2. White Button

**Default State:**
```css
.btn-white {
  background-color: #ffffff;
  color: #000000;
  border: 0;
  padding: 9px 16px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  transition: opacity 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-white:hover {
  opacity: 0.8;
}
```

##### 3. Black Transparent (Outline)

**Default State:**
```css
.btn-black-transparent {
  background-color: transparent;
  color: #000000;
  border: 1px solid rgba(0, 0, 0, 0.3);
  padding: 8px 15px 7px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  transition: border-color 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-black-transparent:hover {
  border-color: rgb(0, 0, 0);
}
```

##### 4. White Transparent (Outline on Dark)

**Default State:**
```css
.btn-white-transparent {
  background-color: transparent;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 8px 15px 7px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  transition: border-color 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-white-transparent:hover {
  border-color: rgb(255, 255, 255);
}
```

##### 5. Black Text (Text-only)

**Default State:**
```css
.btn-text-black {
  background-color: transparent;
  color: #000000;
  border: 0;
  padding: 9px 16px 8px;
  font-size: 13px;
  font-weight: 500;
  transition: opacity 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-text-black:hover {
  opacity: 0.7;
}
```

##### 6. White Text (Text-only on Dark)

**Default State:**
```css
.btn-text-white {
  background-color: transparent;
  color: #ffffff;
  border: 0;
  padding: 9px 16px 8px;
  font-size: 13px;
  font-weight: 500;
  transition: opacity 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-text-white:hover {
  opacity: 0.7;
}
```

##### 7. Accent/Accentuate (Brand Red)

**Default State:**
```css
.btn-accent {
  background-color: #CE0E2D;
  color: #ffffff;
  border: 1px solid #CE0E2D;
  padding: 9px 16px 8px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  transition: background-color 0.3s ease-out;
}
```

**Hover State:**
```css
.btn-accent:hover {
  background-color: #A20A22;
  border-color: #A20A22;
}
```

#### Button Sizes

**Small:**
```css
padding: 10px 17px;
/* or */
padding: 10px 20px;
font-size: 12px;
border-radius: 4px;
```

**Default/Medium:**
```css
padding: 9px 16px 8px;
/* or */
padding: 8px 15px 7px;
font-size: 13px;
border-radius: 6px;
```

**Large:**
```css
padding: 17px 31px 15px;
font-size: 13px;
border-radius: 6px;
```

#### Arrow Buttons

Buttons with animated arrow indicators:

```css
.btn-arrow {
  position: relative;
  padding-right: 32px; /* Extra space for arrow */
}

.btn-arrow::after {
  content: "";
  position: absolute;
  right: 12px;
  top: 50%;
  width: 6px;
  height: 6px;
  border-top: 2px solid currentColor;
  border-right: 2px solid currentColor;
  transform: translateY(-50%) rotate(45deg);
  transition: transform 0.6s ease-out;
}

.btn-arrow:hover::after {
  transform: translateY(-50%) translateX(3px) rotate(45deg);
}
```

#### Button Spacing

```css
.btn {
  margin: 0 12px 16px;
}
```

### Cards

Clean, elevated card components with shadows:

```css
.card {
  background-color: rgb(255, 255, 255);
  border-radius: 8px;
  box-shadow: rgba(0, 0, 0, 0.08) 0px 8px 12px 0px;
  overflow: hidden;
  transition: box-shadow 0.3s ease-out;
}

.card:hover {
  box-shadow: rgba(0, 0, 0, 0.12) 0px 12px 20px 0px;
}

/* Large cards */
.card-large {
  border-radius: 16px;
}

/* Bordered cards (alternative style) */
.card-bordered {
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: rgba(0, 0, 0, 0.01) 0px 3px 6px;
}
```

**Card Content Spacing:**
```css
.card-content {
  padding: 24px;
}

.card-content-large {
  padding: 32px;
}
```

### Form Inputs

#### Search Input

**Desktop:**
```css
.search-input {
  font-size: 24px;
  padding: 32px 12px 12px 44px;
  border: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  background-color: transparent;
}

.search-input::placeholder {
  color: rgb(178, 178, 178);
}
```

**Tablet:**
```css
@media (min-width: 768px) and (max-width: 1079px) {
  .search-input {
    font-size: 22px;
    padding: 36px 15px 34px;
  }
}
```

**Mobile:**
```css
@media (max-width: 767px) {
  .search-input {
    font-size: 22px;
    padding: 24px 15px;
  }
}
```

### Navigation

#### Header

```css
.header {
  height: 78px; /* var(--header_placeholder_height) */
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background-color: #ffffff;
  z-index: 1000;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 1px 2px;
}

/* Placeholder to prevent content jump */
.header-placeholder {
  height: 78px;
}
```

#### Navigation Links

**Desktop:**
```css
.nav-link {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.25;
  padding: 8px 16px;
  color: #000000;
  opacity: 0.6;
  transition: opacity 0.3s ease-out, font-weight 0.3s ease-out;
}

.nav-link:hover,
.nav-link.active {
  opacity: 1;
  font-weight: 700;
}
```

**Mobile:**
```css
@media (max-width: 767px) {
  .nav-link {
    font-size: 16px;
    padding: 12px 20px;
  }
}
```

### Icons

Consistent icon sizing system:

```css
.icon-xs {
  width: 10px;
  height: 10px;
}

.icon-sm {
  width: 16px;
  height: 16px;
}

.icon-md {
  width: 20px;
  height: 20px;
}

.icon-lg {
  width: 22px;
  height: 22px;
}

.icon-xl {
  width: 32px;
  height: 32px;
}

.icon {
  color: #7f7f7f; /* Default gray */
  fill: currentColor;
}
```

---

## Shadows & Elevation

### Shadow Scale

Five shadow levels for creating depth hierarchy:

#### Level 0: Flat
```css
box-shadow: none;
```

#### Level 1: Subtle
```css
box-shadow: rgba(0, 0, 0, 0.01) 0px 3px 6px;
```
**Usage:** Subtle elevation for cards on white backgrounds

#### Level 2: Light
```css
box-shadow: rgba(0, 0, 0, 0.08) 0px 8px 12px 0px;
```
**Usage:** Standard cards, dropdowns, popovers

#### Level 3: Medium
```css
box-shadow: rgba(0, 0, 0, 0.2) 0px 1px 1px 0px inset;
```
**Usage:** Input fields, inset elements

#### Level 4: Strong
```css
box-shadow: rgba(0, 0, 0, 0.5) 0px 0px 4px;
```
**Usage:** Modals, high-priority elements

#### Level 5: Extra Strong (Inset)
```css
box-shadow: rgba(0, 0, 0, 0.3) 0px 0px 0px inset;
```
**Usage:** Pressed states, active inputs

### Z-Index Hierarchy

Systematic stacking order for layers:

| Layer | Z-Index | Usage |
|-------|---------|-------|
| **Base** | `0` - `9` | Normal document flow, cards |
| **Sticky Header** | `100` | Sticky navigation elements |
| **Dropdown** | `1000` | Dropdown menus, popovers |
| **Modal Overlay** | `1001` | Modal backgrounds |
| **Modal Content** | `1002` | Modal dialogs |
| **Tooltip** | `1100` | Tooltips, hints |
| **Notification** | `1200` | Toast notifications |

**Example Usage:**
```css
.header {
  z-index: 100;
}

.dropdown {
  z-index: 1000;
}

.modal-overlay {
  z-index: 1001;
  background-color: rgba(0, 0, 0, 0.6);
}

.modal {
  z-index: 1002;
}

.tooltip {
  z-index: 1100;
  background-color: rgba(0, 0, 0, 0.8);
}
```

### Hover Shadow Transitions

Add depth on interaction:

```css
.card {
  box-shadow: rgba(0, 0, 0, 0.08) 0px 8px 12px 0px;
  transition: box-shadow 0.3s ease-out;
}

.card:hover {
  box-shadow: rgba(0, 0, 0, 0.12) 0px 12px 20px 0px;
}
```

---

## Animations & Transitions

### Transition Timing Scale

Consistent animation durations:

| Name | Duration | Usage |
|------|----------|-------|
| **Instant** | `0.15s` | Micro-interactions, tooltips |
| **Fast** | `0.3s` | Default transitions, hover states |
| **Medium** | `0.4s` - `0.5s` | Component state changes |
| **Slow** | `0.6s` | Arrow animations, complex transitions |
| **Extra Slow** | `0.8s` - `0.9s` | Hero animations, page transitions |

### Timing Functions

#### Default: Ease-Out
```css
transition-timing-function: ease-out;
```
**Usage:** Most transitions (buttons, opacity, colors)

#### Smooth Custom Curve
```css
transition-timing-function: cubic-bezier(0.075, 0.82, 0.165, 1);
```
**Usage:** Smooth, natural-feeling animations

#### Ease-In-Out
```css
transition-timing-function: ease-in-out;
```
**Usage:** Reversible animations (accordion, dropdowns)

### Common Animation Patterns

#### 1. Fade In/Out

```css
/* Initial state */
.fade-element {
  opacity: 0;
  transition: opacity 0.3s ease-out;
}

/* Active state */
.fade-element.active {
  opacity: 1;
}
```

#### 2. Slide Up

```css
/* Initial state */
.slide-up {
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}

/* Active state */
.slide-up.active {
  opacity: 1;
  transform: translateY(0);
}
```

#### 3. Scale In

```css
/* Initial state */
.scale-in {
  opacity: 0;
  transform: scale(0.8);
  transition: opacity 0.4s ease-out, transform 0.4s ease-out;
}

/* Active state */
.scale-in.active {
  opacity: 1;
  transform: scale(1);
}
```

#### 4. Arrow Slide (Hover)

```css
.arrow {
  transition: transform 0.6s ease-out;
}

.button:hover .arrow {
  transform: translateX(3px);
}
```

#### 5. Rotate (Dropdown Icon)

```css
.dropdown-icon {
  transform: rotate(-90deg);
  transition: transform 0.7s cubic-bezier(0.075, 0.82, 0.165, 1);
}

.dropdown.open .dropdown-icon {
  transform: rotate(0deg);
}
```

### Hover State Patterns

#### Opacity Fade

```css
.element {
  opacity: 0.7;
  transition: opacity 0.3s ease-out;
}

.element:hover {
  opacity: 1;
}

/* Reverse pattern (buttons) */
.button {
  opacity: 1;
  transition: opacity 0.3s ease-out;
}

.button:hover {
  opacity: 0.8;
}
```

#### Background Color

```css
.button {
  background-color: #CE0E2D;
  transition: background-color 0.3s ease-out;
}

.button:hover {
  background-color: #A20A22;
}
```

#### Border Color

```css
.outlined-button {
  border: 1px solid rgba(0, 0, 0, 0.3);
  transition: border-color 0.3s ease-out;
}

.outlined-button:hover {
  border-color: rgb(0, 0, 0);
}
```

### Complex Transitions

Multiple properties transitioning together:

```css
.card {
  box-shadow: rgba(0, 0, 0, 0.08) 0px 8px 12px 0px;
  transform: translateY(0);
  transition:
    box-shadow 0.3s ease-out,
    transform 0.3s ease-out;
}

.card:hover {
  box-shadow: rgba(0, 0, 0, 0.12) 0px 12px 20px 0px;
  transform: translateY(-2px);
}
```

### Performance Optimization

Use `transform` and `opacity` for hardware acceleration:

```css
/* Good - GPU accelerated */
.element {
  transform: translate3d(0, 0, 0);
  transition: transform 0.3s ease-out, opacity 0.3s ease-out;
}

/* Avoid - CPU intensive */
.element {
  transition: margin 0.3s ease-out, top 0.3s ease-out;
}
```

---

## Border Radius

### Radius Scale

Systematic border radius values:

| Name | Value | Usage |
|------|-------|-------|
| **None** | `0px` | Square inputs, strict layouts |
| **XS** | `2px` | Subtle rounding, minimal style |
| **SM** | `4px` | Small buttons, form elements |
| **MD** | `6px` | Standard buttons |
| **LG** | `8px` | Cards, search bars, larger buttons |
| **XL** | `12px` | Large cards |
| **2XL** | `16px` | Modal dialogs, hero cards |
| **3XL** | `24px` | Pill-shaped elements |
| **Circle** | `50%` | Avatars, icon buttons, dots |
| **Pill** | `9999px` | Fully rounded pill buttons |

### Component-Specific Radius

**Buttons:**
```css
.btn-small {
  border-radius: 4px;
}

.btn-default {
  border-radius: 6px;
}
```

**Cards:**
```css
.card {
  border-radius: 8px;
}

.card-large {
  border-radius: 16px;
}
```

**Inputs:**
```css
.input {
  border-radius: 0px; /* Square */
}

.search-input {
  border-radius: 8px;
}
```

**Pagination/Indicators:**
```css
.pagination-dot {
  border-radius: 50%;
  width: 8px;
  height: 8px;
}

.pagination-indicator {
  border-radius: 20px;
}
```

**Modals:**
```css
.modal {
  border-radius: 16px;
}
```

### Responsive Radius

Consider reducing radius on mobile for edge-to-edge content:

```css
.card {
  border-radius: 8px;
}

@media (max-width: 767px) {
  .card {
    border-radius: 4px;
  }
}
```

---

## Opacity & Transparency

### Opacity Scale

Systematic opacity levels for consistent layering:

| Level | Value | Usage |
|-------|-------|-------|
| **Invisible** | `0` | Hidden elements (animation start) |
| **Very Light** | `0.3` | Inactive nav items, disabled elements |
| **Medium** | `0.6` | Secondary text, muted elements |
| **Strong** | `0.7` | Hover states |
| **Almost Full** | `0.8` | Button hover, translucent overlays |
| **Full** | `1` | Active, default elements |

### Usage Patterns

#### Interactive States

```css
/* Default inactive */
.nav-item {
  opacity: 0.3;
  transition: opacity 0.3s ease-out;
}

/* Active/hover */
.nav-item:hover,
.nav-item.active {
  opacity: 1;
}
```

#### Button Hover

```css
.button {
  opacity: 1;
  transition: opacity 0.3s ease-out;
}

.button:hover {
  opacity: 0.8;
}
```

#### Disabled States

```css
.button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
```

### Transparent Backgrounds

#### Modal Overlays

```css
.modal-overlay {
  background-color: rgba(0, 0, 0, 0.6);
}
```

#### Tooltips

```css
.tooltip {
  background-color: rgba(0, 0, 0, 0.8);
  color: rgba(255, 255, 255, 1);
}
```

#### Borders

```css
/* Light border on light background */
.outlined {
  border: 1px solid rgba(0, 0, 0, 0.3);
}

/* Light border on dark background */
.outlined-dark {
  border: 1px solid rgba(255, 255, 255, 0.3);
}

/* Subtle divider */
.divider {
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}
```

### Combining Opacity with Transitions

```css
.fade-element {
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease-out, visibility 0.3s ease-out;
}

.fade-element.visible {
  opacity: 1;
  visibility: visible;
}
```

---

## Layout System

### Responsive Breakpoints

The design system uses 3 main breakpoints:

```css
/* Mobile-first approach */

/* Mobile (default) */
/* 0px - 767px */

/* Tablet */
@media (min-width: 768px) and (max-width: 1079px) {
  /* Tablet styles */
}

/* Desktop */
@media (min-width: 1080px) {
  /* Desktop styles */
}

/* Large Desktop */
@media (min-width: 1600px) {
  /* Enhanced desktop styles */
}

/* Extra Large Desktop */
@media (min-width: 2560px) {
  /* Maximum width styles */
}
```

### Container System

#### Max-Width Containers

```css
.container {
  width: 100%;
  max-width: 1350px;
  margin-left: auto;
  margin-right: auto;
  padding-left: 16px;
  padding-right: 16px;
}

@media (min-width: 768px) {
  .container {
    padding-left: 40px;
    padding-right: 40px;
  }
}

@media (min-width: 1080px) {
  .container {
    padding-left: 80px;
    padding-right: 80px;
  }
}

@media (min-width: 1600px) {
  .container {
    padding-left: 80px;
    padding-right: 80px;
  }
}

/* Extra large container */
.container-xl {
  max-width: 2400px;
}
```

#### Full-Width Sections

```css
.section-full {
  width: 100%;
  padding-left: 0;
  padding-right: 0;
}
```

### Flexbox Patterns

#### Horizontal Layout

```css
.flex-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
}
```

#### Vertical Layout

```css
.flex-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
```

#### Space Between

```css
.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
```

#### Centered Content

```css
.flex-center {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

### Grid System

#### Card Grid

```css
.card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 768px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
}

@media (min-width: 1080px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 32px;
  }
}

@media (min-width: 1600px) {
  .card-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
```

#### Negative Margin Grid (Gutter Technique)

```css
.grid-container {
  margin-left: -4px;
  margin-right: -4px;
  display: flex;
  flex-wrap: wrap;
}

.grid-item {
  padding-left: 4px;
  padding-right: 4px;
  width: 100%;
}

@media (min-width: 768px) {
  .grid-item {
    width: 50%;
  }
}

@media (min-width: 1080px) {
  .grid-item {
    width: 33.333%;
  }
}
```

### Sticky/Fixed Elements

#### Fixed Header

```css
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background-color: #ffffff;
}

/* Prevent content jump */
.header-placeholder {
  height: 78px;
}
```

#### Sticky Sidebar

```css
.sidebar {
  position: sticky;
  top: 100px; /* Header height + spacing */
}
```

### Modal Overlay

```css
.modal-overlay {
  position: fixed;
  inset: 0; /* top: 0; right: 0; bottom: 0; left: 0; */
  z-index: 1001;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal {
  position: relative;
  z-index: 1002;
  max-width: 800px;
  width: 90%;
  background-color: #ffffff;
  border-radius: 16px;
  padding: 40px;
}
```

### Aspect Ratio (Images/Videos)

```css
.aspect-ratio-16-9 {
  position: relative;
  width: 100%;
  padding-bottom: 56.25%; /* 9/16 = 0.5625 */
  overflow: hidden;
}

.aspect-ratio-16-9 > img,
.aspect-ratio-16-9 > video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
```

---

## CSS Variables Reference

### Complete List of Custom Properties

```css
:root {
  /* Spacing Variables */
  --pc-margin-top: 80px;
  --pc-margin-bottom: 80px;
  --pad-margin-top: 80px;
  --pad-margin-bottom: 80px;
  --mob-margin-top: 40px;
  --mob-margin-bottom: 40px;

  --padding-top: [dynamic];
  --padding-bottom: [dynamic];
  --padding-top-xs: [dynamic];
  --padding-bottom-xs: [dynamic];

  /* Header */
  --header_placeholder_height: 78px;

  /* Colors */
  --main-title-color: [dynamic];
  --text-color: [dynamic];
  --card-title-color: [dynamic];

  /* Button Colors */
  --btn-font-color: [dynamic]; /* #000 or #fff */
  --btn-bg-color: [dynamic]; /* #000, #fff, or transparent */

  /* Layout */
  --anchor-width: [dynamic];
  --anchor-offset: [dynamic];

  /* Third-party (Swiper) */
  --swiper-theme-color: [dynamic];
  --swiper-navigation-size: [dynamic];
}
```

### Usage Example

```css
.section {
  margin-top: var(--pc-margin-top);
  margin-bottom: var(--pc-margin-bottom);
}

@media (max-width: 767px) {
  .section {
    margin-top: var(--mob-margin-top);
    margin-bottom: var(--mob-margin-bottom);
  }
}

.button {
  color: var(--btn-font-color);
  background-color: var(--btn-bg-color);
}
```

---

## Example Components

### 1. Primary Button Component (React + CSS)

**Button.tsx:**
```tsx
import React from 'react';
import './Button.css';

interface ButtonProps {
  variant?: 'black' | 'white' | 'black-transparent' | 'white-transparent' | 'text-black' | 'text-white' | 'accent';
  size?: 'small' | 'default' | 'large';
  withArrow?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'black',
  size = 'default',
  withArrow = false,
  children,
  onClick,
  disabled = false,
}) => {
  const classNames = [
    'btn',
    `btn-${variant}`,
    `btn-${size}`,
    withArrow && 'btn-arrow',
  ].filter(Boolean).join(' ');

  return (
    <button
      className={classNames}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};
```

**Button.css:**
```css
/* Base button styles */
.btn {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2307;
  letter-spacing: 0;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease-out;
  border: 0;
  outline: none;
  font-family: inherit;
}

.btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Sizes */
.btn-small {
  padding: 10px 17px;
  font-size: 12px;
  border-radius: 4px;
}

.btn-default {
  padding: 9px 16px 8px;
  border-radius: 6px;
}

.btn-large {
  padding: 17px 31px 15px;
  border-radius: 6px;
}

/* Variants */
.btn-black {
  background-color: #000000;
  color: #ffffff;
}

.btn-black:hover:not(:disabled) {
  opacity: 0.8;
}

.btn-white {
  background-color: #ffffff;
  color: #000000;
}

.btn-white:hover:not(:disabled) {
  opacity: 0.8;
}

.btn-black-transparent {
  background-color: transparent;
  color: #000000;
  border: 1px solid rgba(0, 0, 0, 0.3);
}

.btn-black-transparent:hover:not(:disabled) {
  border-color: rgb(0, 0, 0);
}

.btn-white-transparent {
  background-color: transparent;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-white-transparent:hover:not(:disabled) {
  border-color: rgb(255, 255, 255);
}

.btn-text-black {
  background-color: transparent;
  color: #000000;
}

.btn-text-black:hover:not(:disabled) {
  opacity: 0.7;
}

.btn-text-white {
  background-color: transparent;
  color: #ffffff;
}

.btn-text-white:hover:not(:disabled) {
  opacity: 0.7;
}

.btn-accent {
  background-color: #CE0E2D;
  color: #ffffff;
  border: 1px solid #CE0E2D;
}

.btn-accent:hover:not(:disabled) {
  background-color: #A20A22;
  border-color: #A20A22;
}

/* Arrow variant */
.btn-arrow {
  position: relative;
  padding-right: 32px;
}

.btn-arrow::after {
  content: "";
  position: absolute;
  right: 12px;
  top: 50%;
  width: 6px;
  height: 6px;
  border-top: 2px solid currentColor;
  border-right: 2px solid currentColor;
  transform: translateY(-50%) rotate(45deg);
  transition: transform 0.6s ease-out;
}

.btn-arrow:hover::after {
  transform: translateY(-50%) translateX(3px) rotate(45deg);
}
```

**Usage:**
```tsx
<Button variant="black" size="default">
  Learn More
</Button>

<Button variant="accent" withArrow>
  Get Started
</Button>

<Button variant="white-transparent" size="large">
  View Details
</Button>
```

### 2. Card Component (React + CSS)

**Card.tsx:**
```tsx
import React from 'react';
import './Card.css';

interface CardProps {
  title?: string;
  description?: string;
  image?: string;
  children?: React.ReactNode;
  variant?: 'default' | 'large' | 'bordered';
  hoverable?: boolean;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  title,
  description,
  image,
  children,
  variant = 'default',
  hoverable = true,
  onClick,
}) => {
  const classNames = [
    'card',
    `card-${variant}`,
    hoverable && 'card-hoverable',
  ].filter(Boolean).join(' ');

  return (
    <div className={classNames} onClick={onClick}>
      {image && (
        <div className="card-image">
          <img src={image} alt={title} />
        </div>
      )}
      <div className="card-content">
        {title && <h3 className="card-title">{title}</h3>}
        {description && <p className="card-description">{description}</p>}
        {children}
      </div>
    </div>
  );
};
```

**Card.css:**
```css
.card {
  background-color: rgb(255, 255, 255);
  border-radius: 8px;
  box-shadow: rgba(0, 0, 0, 0.08) 0px 8px 12px 0px;
  overflow: hidden;
  transition: box-shadow 0.3s ease-out, transform 0.3s ease-out;
}

.card-hoverable {
  cursor: pointer;
}

.card-hoverable:hover {
  box-shadow: rgba(0, 0, 0, 0.12) 0px 12px 20px 0px;
  transform: translateY(-2px);
}

/* Variants */
.card-large {
  border-radius: 16px;
}

.card-bordered {
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: rgba(0, 0, 0, 0.01) 0px 3px 6px;
}

/* Card sections */
.card-image {
  width: 100%;
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: auto;
  display: block;
  transition: transform 0.4s ease-out;
}

.card-hoverable:hover .card-image img {
  transform: scale(1.05);
}

.card-content {
  padding: 24px;
}

.card-large .card-content {
  padding: 32px;
}

.card-title {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.5;
  color: #1E1E1E;
  margin: 0 0 12px;
}

.card-description {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
  color: #666666;
  margin: 0;
}
```

**Usage:**
```tsx
<Card
  title="Innovation in Technology"
  description="Discover the latest advancements in mobile technology."
  image="/images/product.jpg"
  variant="default"
/>

<Card variant="large" hoverable>
  <h2>Custom Content</h2>
  <p>Any custom content can go here</p>
</Card>
```

### 3. Hero Section Component

**Hero.tsx:**
```tsx
import React from 'react';
import { Button } from './Button';
import './Hero.css';

interface HeroProps {
  title: string;
  subtitle?: string;
  backgroundImage?: string;
  ctaText?: string;
  ctaLink?: string;
  secondaryCtaText?: string;
  secondaryCtaLink?: string;
}

export const Hero: React.FC<HeroProps> = ({
  title,
  subtitle,
  backgroundImage,
  ctaText,
  ctaLink,
  secondaryCtaText,
  secondaryCtaLink,
}) => {
  return (
    <section
      className="hero"
      style={backgroundImage ? { backgroundImage: `url(${backgroundImage})` } : {}}
    >
      <div className="hero-overlay" />
      <div className="hero-content">
        <h1 className="hero-title">{title}</h1>
        {subtitle && <p className="hero-subtitle">{subtitle}</p>}
        {(ctaText || secondaryCtaText) && (
          <div className="hero-actions">
            {ctaText && (
              <Button variant="accent" size="large" withArrow>
                {ctaText}
              </Button>
            )}
            {secondaryCtaText && (
              <Button variant="white-transparent" size="large">
                {secondaryCtaText}
              </Button>
            )}
          </div>
        )}
      </div>
    </section>
  );
};
```

**Hero.css:**
```css
.hero {
  position: relative;
  width: 100%;
  min-height: 600px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-color: #000000;
  overflow: hidden;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.6));
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 1350px;
  width: 100%;
  padding: 0 80px;
  text-align: center;
  color: #ffffff;
}

.hero-title {
  font-size: 40px;
  font-weight: 800;
  line-height: 1.25;
  margin: 0 0 16px;
  opacity: 0;
  transform: translateY(40px);
  animation: slideUp 0.8s ease-out 0.2s forwards;
}

.hero-subtitle {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.6;
  margin: 0 0 32px;
  opacity: 0;
  transform: translateY(40px);
  animation: slideUp 0.8s ease-out 0.4s forwards;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  opacity: 0;
  transform: translateY(40px);
  animation: slideUp 0.8s ease-out 0.6s forwards;
}

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1079px) {
  .hero {
    min-height: 500px;
  }

  .hero-content {
    padding: 0 40px;
  }

  .hero-title {
    font-size: 36px;
  }
}

/* Mobile */
@media (max-width: 767px) {
  .hero {
    min-height: 400px;
  }

  .hero-content {
    padding: 0 16px;
  }

  .hero-title {
    font-size: 24px;
    margin-bottom: 12px;
  }

  .hero-subtitle {
    font-size: 14px;
    margin-bottom: 24px;
  }

  .hero-actions {
    flex-direction: column;
    align-items: center;
  }
}
```

### 4. Navigation Component

**Navigation.tsx:**
```tsx
import React, { useState } from 'react';
import './Navigation.css';

interface NavItem {
  label: string;
  href: string;
}

interface NavigationProps {
  logo: string;
  items: NavItem[];
  currentPath?: string;
}

export const Navigation: React.FC<NavigationProps> = ({
  logo,
  items,
  currentPath = '/',
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      <div className="header-placeholder" />
      <header className="header">
        <div className="header-container">
          <div className="header-logo">
            <img src={logo} alt="Logo" />
          </div>

          <nav className="nav-desktop">
            {items.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className={`nav-link ${currentPath === item.href ? 'active' : ''}`}
              >
                {item.label}
              </a>
            ))}
          </nav>

          <button
            className="nav-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <span />
            <span />
            <span />
          </button>
        </div>

        {mobileMenuOpen && (
          <nav className="nav-mobile">
            {items.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className={`nav-link ${currentPath === item.href ? 'active' : ''}`}
                onClick={() => setMobileMenuOpen(false)}
              >
                {item.label}
              </a>
            ))}
          </nav>
        )}
      </header>
    </>
  );
};
```

**Navigation.css:**
```css
.header-placeholder {
  height: 78px;
}

.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 78px;
  background-color: #ffffff;
  z-index: 100;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 1px 2px;
}

.header-container {
  max-width: 1350px;
  height: 100%;
  margin: 0 auto;
  padding: 0 80px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-logo img {
  height: 32px;
  display: block;
}

/* Desktop Navigation */
.nav-desktop {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-link {
  font-size: 12px;
  font-weight: 500;
  line-height: 1.25;
  letter-spacing: 0.3px;
  padding: 8px 16px;
  color: #000000;
  text-decoration: none;
  opacity: 0.6;
  transition: opacity 0.3s ease-out, font-weight 0.3s ease-out;
}

.nav-link:hover,
.nav-link.active {
  opacity: 1;
  font-weight: 700;
}

/* Mobile Toggle */
.nav-toggle {
  display: none;
  flex-direction: column;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
}

.nav-toggle span {
  width: 24px;
  height: 2px;
  background-color: #000000;
  transition: all 0.3s ease-out;
}

/* Mobile Navigation */
.nav-mobile {
  display: none;
  flex-direction: column;
  background-color: #ffffff;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  padding: 16px 0;
}

.nav-mobile .nav-link {
  font-size: 16px;
  padding: 12px 20px;
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1079px) {
  .header-container {
    padding: 0 40px;
  }
}

/* Mobile */
@media (max-width: 767px) {
  .header-container {
    padding: 0 16px;
  }

  .nav-desktop {
    display: none;
  }

  .nav-toggle {
    display: flex;
  }

  .nav-mobile {
    display: flex;
  }
}
```

### 5. Grid Layout Example

**ProductGrid.tsx:**
```tsx
import React from 'react';
import { Card } from './Card';
import './ProductGrid.css';

interface Product {
  id: string;
  title: string;
  description: string;
  image: string;
}

interface ProductGridProps {
  products: Product[];
}

export const ProductGrid: React.FC<ProductGridProps> = ({ products }) => {
  return (
    <section className="section">
      <div className="container">
        <h2 className="section-title">Our Products</h2>
        <div className="product-grid">
          {products.map((product) => (
            <Card
              key={product.id}
              title={product.title}
              description={product.description}
              image={product.image}
              variant="default"
              hoverable
            />
          ))}
        </div>
      </div>
    </section>
  );
};
```

**ProductGrid.css:**
```css
.section {
  margin-top: 80px;
  margin-bottom: 80px;
}

.container {
  max-width: 1350px;
  margin: 0 auto;
  padding: 0 80px;
}

.section-title {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.321;
  color: #1E1E1E;
  margin: 0 0 40px;
  text-align: center;
}

.product-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1079px) {
  .section {
    margin-top: 80px;
    margin-bottom: 80px;
  }

  .container {
    padding: 0 40px;
  }

  .section-title {
    font-size: 24px;
  }

  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }
}

/* Desktop */
@media (min-width: 1080px) {
  .product-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 32px;
  }
}

/* Large Desktop */
@media (min-width: 1600px) {
  .product-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* Mobile */
@media (max-width: 767px) {
  .section {
    margin-top: 40px;
    margin-bottom: 40px;
  }

  .container {
    padding: 0 16px;
  }

  .section-title {
    font-size: 20px;
    margin-bottom: 24px;
  }
}
```

---

## Implementation Guidelines

### Best Practices

1. **Mobile-First Approach**: Always start with mobile styles and enhance for larger screens
2. **CSS Variables**: Use CSS custom properties for theme-related values
3. **Consistent Transitions**: Use the 0.3s default for most interactions
4. **Semantic HTML**: Use appropriate HTML5 semantic elements
5. **Accessibility**: Ensure WCAG AA compliance (4.5:1 contrast ratio minimum)
6. **Performance**: Use `transform` and `opacity` for animations
7. **Component Reusability**: Build modular, composable components
8. **Responsive Images**: Use `srcset` and `picture` elements for optimal image loading

### Code Quality

- **CSS**: Use BEM naming convention or CSS Modules
- **TypeScript**: Enable strict mode, define all types
- **Testing**: Write tests for all interactive components
- **Documentation**: Document component props and usage

### Performance Optimization

```css
/* Use will-change for animated elements */
.animated-element {
  will-change: transform, opacity;
}

/* Remove will-change after animation */
.animated-element.animation-complete {
  will-change: auto;
}

/* Use hardware acceleration */
.accelerated {
  transform: translate3d(0, 0, 0);
}
```

### Accessibility Checklist

- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Interactive elements have visible focus states
- [ ] Buttons have descriptive labels
- [ ] Images have alt text
- [ ] Forms have proper labels
- [ ] Keyboard navigation works properly
- [ ] ARIA attributes where necessary

---

## Design Tokens Summary

### Quick Reference

```css
/* Colors */
--color-black: #000000;
--color-white: #FFFFFF;
--color-red: #CE0E2D;
--color-red-hover: #A20A22;
--color-text-primary: #1E1E1E;
--color-text-secondary: #666666;
--color-border: #E3E3E3;
--color-background: #F5F5F5;

/* Typography */
--font-size-xs: 12px;
--font-size-sm: 14px;
--font-size-base: 16px;
--font-size-lg: 20px;
--font-size-xl: 24px;
--font-size-2xl: 28px;
--font-size-3xl: 36px;
--font-size-4xl: 40px;

--font-weight-regular: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;
--font-weight-extrabold: 800;

--line-height-tight: 1.25;
--line-height-normal: 1.5;
--line-height-relaxed: 1.6;

/* Spacing */
--spacing-xs: 8px;
--spacing-sm: 12px;
--spacing-md: 16px;
--spacing-lg: 24px;
--spacing-xl: 32px;
--spacing-2xl: 40px;
--spacing-3xl: 80px;

/* Border Radius */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-xl: 16px;
--radius-full: 50%;

/* Shadows */
--shadow-sm: rgba(0, 0, 0, 0.01) 0px 3px 6px;
--shadow-md: rgba(0, 0, 0, 0.08) 0px 8px 12px 0px;
--shadow-lg: rgba(0, 0, 0, 0.12) 0px 12px 20px 0px;

/* Transitions */
--transition-fast: 0.15s;
--transition-base: 0.3s;
--transition-slow: 0.6s;
--transition-timing: ease-out;
```

---

## Conclusion

This style guide captures the essence of HUAWEI's design system: **minimalist, high-contrast, and fluid**. The system prioritizes:

- **Clarity** through strong typography hierarchy
- **Elegance** with subtle shadows and smooth transitions
- **Consistency** via reusable components and tokens
- **Performance** with optimized animations and responsive patterns

Use this guide as a foundation for building modern, accessible, and visually cohesive web applications that embody HUAWEI's design philosophy.

---

*Style Guide v1.0 | Generated from HUAWEI Global website analysis | Last updated: 2025*
