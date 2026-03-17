# UI/UX Pro Max - Master Design System
## Project: Forecasting Licores Dashboard

### 1. Style Guidelines
- **Theme**: Dark Mode (Premium / Luxury)
- **Aesthetic**: Glassmorphism with deep shadows and soft volumetric highlights.
- **Industry**: Liquor / Beverage / Analytics
- **Primary Vibe**: Elegant, authoritative, and data-dense but deeply readable.

### 2. Color Palette (Dark Mode)
- **Background Base**: `#0A0A0A` (Deepest neutral black)
- **Surface**: `#141414` (Slightly lighter dark core)
- **Surface Glass**: `rgba(20, 20, 20, 0.6)` with backdrop-filter `blur(12px)`
- **Primary (Accent)**: `#D9A05B` (Aged Gold / Whiskey tone, used for CTAs and highlighted data)
- **Secondary (Accent 2)**: `#8C2E2A` (Deep Wine Red, used for secondary graphs or contrasting data)
- **Text Primary**: `#F8F8F8` (High contrast white)
- **Text Secondary**: `#A1A1AA` (Zinc-400 for muted text and table headers)
- **Borders**: `#27272A` (Zinc-800, very subtle separating lines)
- **Success/Growth**: `#10B981` (Emerald)
- **Warning/Decrease**: `#EF4444` (Red)

### 3. Typography
- **Headings (H1, H2, H3)**: `Playfair Display` (Serif. Brings the luxury and traditional liquor aesthetic)
- **Body & Data (Tables, Charts, Labels)**: `Inter` (Sans-serif. Highly legible for dashboards and tiny numbers)
- **Numbers/Metrics**: Use tabular nums in `Inter` (`font-variant-numeric: tabular-nums`).

### 4. Layout & Spacing
- **Pattern**: Bento Grid Layout for widgets (assymetrical but perfectly aligned boxes).
- **Container**: `max-w-7xl` or full-width with `px-8` padding.
- **Gap Spacing**: Generous. Use `gap-6` or `gap-8` for grid elements.
- **Border Radius**: `rounded-2xl` for cards, very smooth and modern edges.

### 5. Interaction & Animation (UX Rules)
- **Hover States**: Cards should elevate subtly (using `translate-y-[-2px]` and softer box-shadow).
- **Transitions**: `transition-all duration-300 ease-in-out`
- **Cursor**: Always use `cursor-pointer` for interactive elements.
- **No layout shift on hover**: Only use transforms (scale/translate) or opacity changes.
- **Empty States & Hero Features**: Perfect use-case for 3D/high-fidelity assets injected via Nano Banana 2.

### 6. Accessibility (A11Y)
- **Contrast**: Text over glass/background must maintain 4.5:1 ratio minimum.
- **Focus**: `ring-2 ring-[#D9A05B] ring-offset-2 ring-offset-[#0A0A0A]`
- **Icons**: No emojis. Use Lucide React or Heroicons (SVG only).
