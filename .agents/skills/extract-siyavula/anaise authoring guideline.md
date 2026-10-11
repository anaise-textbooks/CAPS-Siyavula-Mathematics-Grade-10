# Anaise Curriculum & Content Authoring Guidelines

This guide details how to author, organize, and publish educational content for the Anaise learning platform. It defines the formal specification for **Book Repositories** (reusable text, media, and interactive exercises) and **Module/Curriculum Repositories** (syllabi, degree tracks, and learning progression).

---

## 1. System Model: Decoupled Modules vs. Books

Anaise cleanly separates pedagogical structure from content libraries:

* **Book Repositories (`1 Book = 1 Git Repo`):** Standalone learning texts, lab assignments, media, and practice checks. They are self-contained, agnostic of how an institution grades or structures a degree, and maintain their own commit history.
* **Module Repositories (`Curriculum / Syllabus`):** Orchestrators managed by instructors or academic administrators. Modules map learning outcomes to specific book chapters, define prerequisites, enforce completion thresholds, and attach course-specific quizzes.

```
┌────────────────────────────────────────────────────────┐
│             Module / Curriculum Repository             │
│   (Orchestrates syllabus, outcomes, & prerequisites)   │
└───────────────────────────┬────────────────────────────┘
                            │ References / Pinned SHAs
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│     Book Repository A     │ │     Book Repository B     │
│  (Data Structures in C)   │ │   (System Architecture)   │
│  Chapters, Assets, Labs   │ │  Chapters, Assets, Labs   │
└───────────────────────────┘ └───────────────────────────┘

```

---

## 2. Book Repository Specification

A Book repository represents an interactive digital textbook or lab manual.

### Recommended Directory Layout

```text
my-book-repo/
├── book.manifest.json            # Book metadata and chapter table of contents
├── assets/                       # Images, diagrams, datasets
│   └── architecture-diagram.png
└── chapters/
    ├── 01-intro/
    │   ├── 01-overview.mdx
    │   └── 02-architecture.mdx
    └── 02-data-structures/
        ├── 01-pointers.mdx
        └── 02-linked-lists.mdx

```

### Book Manifest (`book.manifest.json`)

```json
{
  "$schema": "https://anaise.org/schemas/book.v1.json",
  "id": "book-modern-systems",
  "title": "Modern Systems Programming with C",
  "subtitle": "A pragmatic introduction to bare-metal architectures.",
  "version": "1.4.0",
  "coverImage": null,
  "thumbnail": null,
  "authors": [
    { "name": "Dr. Sarah Chen", "affiliation": "Systems Lab" }
  ],
  "license": "CC-BY-4.0",
  "toc": [
    {
      "id": "ch01",
      "title": "Chapter 1: Foundational Architecture",
      "sections": [
        {
          "id": "sec-01-overview",
          "title": "System Memory Layout",
          "path": "chapters/01-intro/01-overview.mdx",
          "estimatedMinutes": 20
        },
        {
          "id": "sec-02-arch",
          "title": "Pointers and Memory Addressing",
          "path": "chapters/01-intro/02-architecture.mdx",
          "estimatedMinutes": 35
        }
      ]
    }
  ]
}

```

#### Cover Image & Thumbnail Field Specifications
* **`coverImage` (`string | null`):** The primary banner / hero image for the textbook module.
  * **Relative Path:** e.g. `./assets/images/cover.png` or `assets/images/cover.png` — automatically resolved by the Anaise viewer to the repository's raw asset URL.
  * **Absolute URL:** e.g. `https://images.unsplash.com/...` or direct CDN URL — rendered directly.
  * **`null` or omitted:** When set to `null`, `""`, or omitted, the Anaise viewer dynamically applies a curated, high-contrast random cover image based on the subject category.
* **`thumbnail` (`string | null`):** The catalog card / course grid preview image.
  * Supports relative paths, absolute URLs, or `null`.
  * If `null` or omitted, the viewer falls back to `coverImage` or the dynamic category fallback image.

---

## 3. Module & Curriculum Repository Specification

A Module repository orchestrates courses, units, and learning outcomes, referencing one or more books.

### Repository Resolution & Version Pinning

* **Version Pinning:** A module manifest can pin an external book to a specific `commitSha` or release tag.
* **Default Behavior:** If no `commitSha` is supplied, Anaise fetches the latest commit on the repository's default branch.
* **Failure Handling:** If a remote file is missing, the repository is unavailable, or a branch rename occurs, the system logs an upstream sync fault, presents an alert in the admin dashboard, and serves an actionable error notice to the student.

### Module Manifest (`module.manifest.json`)

```json
{
  "$schema": "https://anaise.org/schemas/module.v1.json",
  "id": "cs-102",
  "title": "CS102: Data Structures & Algorithms",
  "level": "Intermediate",
  "prescribedSources": [
    {
      "id": "systems-book",
      "repoUrl": "https://github.com/academic-systems/modern-systems-programming",
      "commitSha": "4f8a3c10b" 
    },
    {
      "id": "dsa-reference",
      "repoUrl": "https://github.com/academic-systems/algorithms-core"
    }
  ],
  "units": [
    {
      "id": "unit-01-memory",
      "title": "Unit 1: Memory & Indirection",
      "learningOutcomes": [
        "Explain stack and heap allocation lifecycles",
        "Calculate pointer offsets in contiguous buffers"
      ],
      "lessons": [
        {
          "id": "lesson-01",
          "title": "Memory Layout",
          "source": "systems-book",
          "path": "chapters/01-intro/01-overview.mdx"
        },
        {
          "id": "lesson-02",
          "title": "Pointer Math & Memory Strides",
          "source": "systems-book",
          "path": "chapters/01-intro/02-architecture.mdx",
          "prerequisites": ["lesson-01"],
          "quizOverride": "local-assessments/unit-01-exam.json"
        }
      ]
    }
  ]
}

```

---

## 4. Assessment & Quiz Inheritance Rules

To keep authoring flexible and prevent merge friction, Anaise uses a **Clean Fork / Full-Override** model for assessments:

1. **Direct Inheritance (Default):** If a lesson references an external book chapter, all embedded `http://googleusercontent.com/immersive_entry_chip/0` elements inside that chapter evaluate natively as built-in knowledge checks.
2. **Course Overrides (`quizOverride`):** If an instructor wants to replace a chapter's self-study quiz with a university-specific graded exam:
* The instructor creates a standalone quiz file (e.g., `local-assessments/unit-01-exam.json`) inside the module repository.
* The module manifest points to this path via `quizOverride`.
* Anaise suppresses the chapter’s default self-checks and displays the custom course assessment instead.
* *No fragile line-by-line question patching or diffing is performed.*



---

## 5. Media & Asset Linking Rules

Content frequently references static media (diagrams, images, local audio/video clips). Anaise supports both direct and relative links, using a deterministic fallback strategy:

```markdown
<!-- Dual Link Convention (Relative with Direct Fallback) -->
![Memory Layout](./assets/architecture-diagram.png)

<!-- Direct Remote Asset -->
![Cloud Storage Architecture](https://assets.university.edu/images/cloud-arch.png)

```

### Path Resolution Order

1. **Direct Absolute URLs (`https://...`):** Rendered as-is directly from the source host.
2. **Relative URLs (`./assets/...`):**
* The reader engine parses the current lesson file's location inside the source Git repository.
* It translates `./assets/example.png` into the raw Git CDN link:
`[https://raw.githubusercontent.com/](https://raw.githubusercontent.com/){owner}/{repo}/{commitSha}/{currentDirectory}/assets/example.png`


3. **Fallback Policy:** If the rewritten relative CDN path returns a 404 error, the engine attempts resolution against the repository root `/assets/` directory before rendering a placeholder with a broken asset alert.

---

## 6. MDX/JSX Interactive Component Library

All dynamic lessons use standard **MDX/JSX** syntax. Authors and visual editors insert declarative tags directly into the markdown body.

### `<Callout>`

Highlights context, definitions, or warnings.

```mdx
<Callout type="warning" title="Memory Bounds">
  Never dereference pointers without first validating allocation bounds.
</Callout>

```

* **Props:**
* `type` (required): `"info"` | `"tip"` | `"warning"` | `"danger"` | `"note"`
* `title` (optional): Header string.



---

### `<VideoPlayer>`

Responsive video component supporting streaming services and direct cloud storage links.

```mdx
<VideoPlayer 
  src="https://www.youtube.com/watch?v=sample-video"
  title="Visualizing Stack Frame Pointer Steps"
  duration="08:45"
  trackProgress={true}
/>

```

* **Props:**
* `src` (required): Video URL (YouTube, Vimeo, or raw `.mp4` link).
* `title` (required): Media description.
* `duration` (optional): Formatted string (e.g., `"12:30"`).
* `trackProgress` (optional, boolean): If `true`, requires 80% playback completion before lesson completion unlocks.



---

### `

---

## 7. Authoring Checklist

Before committing or pushing material through the visual editor:

* [ ] **Manifest Validation:** Ensure `book.manifest.json` or `module.manifest.json` conforms to the JSON schema.
* [ ] **Asset Paths:** Relative paths use `./assets/...` conventions and referenced media files exist in the commit.
* [ ] **Quiz IDs & Options:** Each `http://googleusercontent.com/immersive_entry_chip/2` component has unique options and the `correctOptionId` maps to an existing choice ID.
* [ ] **Prerequisite Chain:** Any lesson ID listed in a module's `prerequisites` array exists and appears earlier in the syllabus sequence.