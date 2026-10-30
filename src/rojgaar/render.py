"""Render drafts to Markdown (always) and to RenderCV YAML (for PDF via the optional
``render`` extra). Personal details are filled in locally from ``pii.yaml`` at the
very last step; prompts and drafts only ever contain ``{{PLACEHOLDERS}}``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import yaml

from .bank import Bank
from .truth import Draft

PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def fill_placeholders(text: str, pii: dict[str, str]) -> str:
    return PLACEHOLDER.sub(lambda m: str(pii.get(m.group(1), m.group(0))), text)


def draft_to_markdown(draft: Draft, bank: Bank, with_src: bool = False) -> str:
    out = ["# {{NAME}}", "{{EMAIL}} · {{PHONE}} · {{LOCATION}}", ""]
    if draft.summary:
        out += [
            "## Summary",
            draft.summary.text + (f"  <!-- src: {', '.join(draft.summary.src)} -->" if with_src else ""),
            "",
        ]
    for section in draft.sections:
        out.append(f"## {section.title}")
        for b in section.bullets:
            out.append(f"- {b.text}" + (f"  <!-- src: {', '.join(b.src)} -->" if with_src else ""))
        out.append("")
    if draft.skills:
        out += ["## Skills", ", ".join(draft.skills), ""]
    if bank.education:
        out.append("## Education")
        for e in bank.education:
            out.append(
                f"- {e.degree}" + (f", {e.school}" if e.school else "") + (f" ({e.end})" if e.end else "")
            )
        out.append("")
    return "\n".join(out)


def cover_letter_to_markdown(draft: Draft) -> str:
    cl = draft.cover_letter
    if not cl:
        return ""
    parts = ["{{NAME}}", "{{EMAIL}} · {{PHONE}}", "", "Dear Hiring Team,", ""]
    parts.append(cl.motivation or "[WRITE OR CONFIRM YOUR MOTIVATION LINE]")
    parts.append("")
    for p in cl.paragraphs:
        parts += [p.text, ""]
    if cl.closing:
        parts += [cl.closing, ""]
    parts += ["Sincerely,", "{{NAME}}"]
    return "\n".join(parts) + "\n"


def draft_to_rendercv(draft: Draft, bank: Bank, pii: dict[str, str], theme: str = "classic") -> dict:
    """Build a RenderCV input document (single-column theme, standard headings)."""
    sections: dict[str, list] = {}
    if draft.summary:
        sections["summary"] = [fill_placeholders(draft.summary.text, pii)]
    for section in draft.sections:
        sections[section.title.lower().replace(" ", "_")] = [
            {"bullet": fill_placeholders(b.text, pii)} for b in section.bullets
        ]
    if draft.skills:
        sections["skills"] = [{"label": "Skills", "details": ", ".join(draft.skills)}]
    if bank.education:
        sections["education"] = [
            {"institution": e.school or "", "area": e.degree, "end_date": e.end or ""} for e in bank.education
        ]
    return {
        "cv": {
            "name": pii.get("NAME", ""),
            "email": pii.get("EMAIL") or None,
            "phone": pii.get("PHONE") or None,
            "location": pii.get("LOCATION") or None,
            "sections": sections,
        },
        "design": {"theme": theme},
    }


def render_pdf(rendercv_yaml: Path, out_dir: Path) -> Path | None:
    """Render with RenderCV if installed. Returns the PDF path or None."""
    exe = shutil.which("rendercv")
    if not exe:
        return None
    subprocess.run(
        [exe, "render", str(rendercv_yaml), "--output-folder-name", str(out_dir)], check=True, timeout=180
    )
    pdfs = sorted(out_dir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def write_rendercv_yaml(doc: dict, path: Path) -> Path:
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path
