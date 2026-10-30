# P3-04 · Render: RenderCV PDF, pandoc DOCX, parse-back

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 3 · Drafting + truthfulness | 2 days | P3-01 | todo |

## Why
Rendering is deterministic, so it belongs in code. RenderCV is MIT, installs with pip and uses Typst (no LaTeX). Some portals want DOCX. A parse-back test proves an ATS can read the text.

## What to do
- [ ] Map draft → RenderCV YAML (`cv.yaml`, each bullet with a trailing `# src:` comment); render `cv.pdf` with a single-column theme, US Letter, standard headings.
- [ ] `cv.docx` via `pandoc --reference-doc templates/reference.docx`.
- [ ] Parse-back: extract PDF text with `pdftotext`; confirm every bullet, heading and contact placeholder survives in order.
- [ ] Never white-text keywords or hidden text of any kind.

## Done when
- Rendering 5 drafts produces PDF + DOCX; parse-back recovers 100% of bullets for each.
