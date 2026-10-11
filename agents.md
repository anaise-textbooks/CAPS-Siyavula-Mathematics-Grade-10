# CAPS Siyavula Mathematics Grade 10 Content Repository

## Project Role & Mission
This repository houses the digital textbook content for **CAPS Siyavula Mathematics Grade 10**, structured strictly according to the **Anaise Curriculum & Content Authoring Guidelines** (`anaise authoring guideline.md`).

## System Model & Repository Boundaries
- **1 Book = 1 Git Repo**: This repository is a standalone Book Repository adhering to the Anaise Book specification.
- Modules/curriculums reside in separate orchestrator repositories that reference this repository.
- Metadata and table of contents are declared in `book.manifest.json`.

## Repository Structure & Standards
```text
CAPS-Siyavula-Mathematics-Grade-10/
├── book.manifest.json            # Book metadata and chapter table of contents
├── assets/                       # Global diagrams, figures, and media
│   └── images/
├── chapters/
│   ├── 01-algebraic-expressions/
│   │   ├── 01-introduction.mdx
│   │   ├── 02-the-real-number-system.mdx
│   │   └── ...
│   └── ...
└── .agents/
    └── skills/
        └── extract-siyavula/
            └── SKILL.md
```

## Content Extraction & Authoring Rules
1. **File Format**: All chapter sections must be saved as `.mdx` files under `chapters/<chapter-slug>/<section-slug>.mdx`.
2. **Interactive Components & Exercises**:
   - Callouts and tips use `<Callout type="info|tip|warning|danger|note" title="...">...</Callout>`.
   - Embedded educational videos use `<VideoPlayer src="..." title="..." />`.
   - Quizzes, worked examples, and problem sets must preserve question statements, hints, and step-by-step solutions with `**Problem:**` and `**Solution:**` tokens.
   - Solutions are interactive and hidden by default in the Anaise platform, revealing step-by-step guidance only upon learner demand.
   - **Non-Gradable Textbook Exercises**: When exercises do not have digital auto-grading keys, do not present misleading empty input forms or buttons. Structure them as collapsible worked problems with `**Problem:**` and `**Solution:**` blocks or explicit textbook references.
3. **Dedicated Exercise / Quiz Topics**:
   - Standalone problem sets and "End of chapter exercises" are classified as dedicated `quiz` checkpoints in the platform rather than static readings.
   - Major textbook exercise sections must use clear headings (e.g. `### Textbook Exercises`) so that the reader engine can generate collapsible accordion containers that link seamlessly to content navigators.
4. **List & Prose Integrity**:
   - Bulleted and numbered lists with formulas or multiple sentences must preserve list continuation lines so they do not break into fragmented or misplaced items.
5. **Math & Formulae**:
   - Math expressions are rendered using KaTeX / LaTeX syntax: inline with `\(...\)` or `$...$`, and display math with `\[...\]`, `$$...$$`, or `\begin{align*} ... \end{align*}`.
   - Preserve clean LaTeX symbols and notation (e.g. `\mathbb{N}`, `\frac{a}{b}`, `\sqrt{x}`).
6. **Media & Assets**:
   - Downloaded diagrams, figures, and illustrations must be saved in `assets/images/` with unique hash names or descriptive slugs.
   - Referenced in `.mdx` files via relative links: `![Alt Text](../../assets/images/filename.png)` or `./assets/images/filename.png`.
   - **Alpha Channel Awareness**: Diagrams and geometric graphs frequently contain transparent backgrounds with black lines originally meant for white paper. The Anaise viewer isolates these on high-contrast surface backdrops, but source assets must avoid baked-in dark-background assumptions.
   - No dead links or missing images.
7. **Content Navigation & Anchors**:
   - All section headers and exercise checkpoints must have deterministic titles and slug anchors (`heading-{index}-{slug}`) to ensure dual navigation support across sidebar accordions and on-page sticky navigators.
8. **Manifest & Nomenclature Integrity**:
   - `book.manifest.json` must be kept in sync with all chapters and sections in `chapters/`.
   - Every section must specify `id`, `title`, `path`, and realistic `estimatedMinutes`.
   - `coverImage` and `thumbnail` fields in the manifest accept relative paths (e.g. `./assets/images/cover.png`), absolute URLs, or `null`. When `null` or unassigned, the Anaise viewer automatically applies a dynamic category cover fallback.
   - Content structure aligns with the **South Africa & Commonwealth** nomenclature standard (`Programme / Module / Unit / Topic`).
