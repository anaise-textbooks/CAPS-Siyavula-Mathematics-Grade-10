---
name: extract-siyavula
description: >-
  Extract, clean, and convert Siyavula curriculum textbooks (HTML, EPUB, PDF) into Anaise-compliant
  Book repositories with MDX lessons, KaTeX mathematics, assets, and book.manifest.json. Use whenever
  extracting, updating, or maintaining Siyavula educational content for Anaise.
---

# Siyavula Content Extraction & Conversion Skill

This skill governs the end-to-end extraction and transformation of Siyavula textbooks into the **Anaise Book Repository** format defined in `anaise authoring guideline.md`.

## Workflow Overview

```mermaid
flowchart TD
    A["Parse Table of Contents (Web/HTML)"] --> B["Build Chapter & Section Hierarchy"]
    B --> C["Fetch Section HTML & Clean Chrome/Banners"]
    C --> D["Download Media into assets/images/"]
    D --> E["Convert Content to MDX + LaTeX Math"]
    E --> F["Wrap Callouts, Videos, and Interactive Checks"]
    F --> G["Identify & Classify Quiz vs Reading Sections"]
    G --> H["Generate book.manifest.json"]
    H --> I["Validate Integrity & Asset Resolution"]
```

## 1. Extraction Specifications

### Content Sanitization
- Remove extraneous Siyavula navigation bars, banners (`sv-book-banner`), marketing blocks, breadcrumbs, and footer links.
- Retain all core pedagogical content:
  - Theoretical prose and definitions (`<dl class="definition">` converted to semantic definitions or `<Callout type="info">`).
  - Bulleted and enumerated lists (preserve multiline text items without premature line jumping).
  - Worked examples with problems, work steps, and solutions.
  - End-of-chapter exercises and solutions (`problemset`, `entry`, `problem`, `solution`).

### Interactive Components & Knowledge Checks
- **Interactive Practice Problems & Solutions**:
  - Exercises, textbook problems, and end-of-chapter questions are structured with explicit problem and solution blocks:
    ```markdown
    **Problem:**
    Find the values of \(x\) for which the expression is undefined.

    **Solution:**
    Set the denominator equal to zero: \(x^2 - 4 = 0 \implies x = \pm 2\).
    ```
  - The Anaise rendering platform automatically wraps `**Solution:**` blocks in an interactive `SolutionToggle` component, **collapsing and hiding answers by default** until the student clicks *"Show Answer & Explanation"*.
  - **No Empty / Misleading Answer Forms**: For open-ended textbook exercises where digital auto-grading is unavailable, do not inject dummy input fields or submission buttons. Present the exercise problem directly, and provide the step-by-step solution block or direct reference to the textbook solution.
  - **Collapsible Textbook Exercise Sections**: Group problem sets under clear headers (e.g. `### Textbook Exercises`). The Anaise reader renders these as collapsible sections (`defaultOpen={false}`) that auto-expand when navigated to from table of contents anchors.
- **Callouts**:
  ```mdx
  <Callout type="note" title="Decimal Notation">
    You may see a full stop instead of a comma used to indicate a decimal number.
  </Callout>
  ```
- **Videos**:
  ```mdx
  <VideoPlayer
    src="https://www.youtube.com/watch?v=..."
    title="Video Walkthrough"
  />
  ```

### Mathematical Notation
- Inline LaTeX math formatted as `\(...\)` or `$...$`.
- Display / block equations formatted as `\[...\]` or `$$...$$`, or `\begin{align*} ... \end{align*}`.
- Ensure escaped characters and fractions (`\frac{...}{...}`) are cleanly preserved.

### Media & Assets
- Download all figures, geometry graphs, and illustrations to `assets/images/`.
- **Transparent Image Backgrounds**: Many Siyavula illustrations contain transparent backgrounds with black lines originally designed for light pages. While the Anaise platform wraps diagrams on surface-isolated backgrounds for dark and academic themes, ensure extracted images do not assume a single dark theme or invert colors indiscriminately.

### Content Navigation Anchors
- Heading anchors are generated deterministically (`heading-{index}-{slug}`). Ensure titles and section headings are consistent so that both the on-page navigator ("On this page") and the sidebar lesson accordion can scroll directly to the target element and expand its accordion container.

### List Formatting Rules
- Siyavula lists containing equations, fractions, or multi-sentence descriptions must be continuous.
- Do not split sentences across separate bullet points; preserve list continuation indentation so the reader engine treats each bullet as a single cohesive item.

### Section Classification & Manifest Generation
- `book.manifest.json` conforms to `https://anaise.org/schemas/book.v1.json`.
- **Cover Image & Thumbnail**: Manifests include `"coverImage": null` and `"thumbnail": null` by default. Authors can populate them with relative paths (e.g. `./assets/images/cover.png`) or absolute URLs. When `null`, the Anaise viewer applies dynamic category covers automatically.
- **Dedicated Quiz Units**: Sections containing end-of-chapter exercises or standalone problem sets (`End of chapter exercises`, `Textbook Exercise`) are identified and mapped as `type: 'quiz'` in the course orchestrator/manifest, separating conceptual readings from interactive exercise checkpoints.
- Each chapter lists all sections, paths to `.mdx` files, and realistic reading/practice time estimates (`estimatedMinutes`).
- **Academic Nomenclature Standard**: Default to **South Africa & Commonwealth** convention (`Programme / Module / Unit / Topic`).
