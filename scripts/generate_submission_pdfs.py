import re
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

DOC_MAP = [
    (
        Path("docs/Case_Study_3_Submission_Draft.md"),
        Path("docs/submission_pdfs/Case_Study_3_Submission_Draft.pdf"),
        "Case_Study_3_Submission_Draft",
    ),
    (
        Path("docs/level2/Proof_of_Concept.md"),
        Path("docs/submission_pdfs/Proof_of_Concept.pdf"),
        "Proof_of_Concept",
    ),
    (
        Path("docs/level3/Working_Prototype.md"),
        Path("docs/submission_pdfs/Working_Prototype.pdf"),
        "Working_Prototype",
    ),
    (
        Path("docs/security/Security_Hardening_Plan_and_Implementation.md"),
        Path("docs/submission_pdfs/Security_Hardening_Plan_and_Implementation.pdf"),
        "Security_Hardening_Plan_and_Implementation",
    ),
]

LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="H1X",
            parent=styles["Heading1"],
            fontSize=14,
            leading=17,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2X",
            parent=styles["Heading2"],
            fontSize=10.5,
            leading=13,
            spaceBefore=4,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyX",
            parent=styles["BodyText"],
            fontSize=9.3,
            leading=11.5,
            spaceAfter=1.2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletX",
            parent=styles["BodyText"],
            fontSize=9.3,
            leading=11.5,
            leftIndent=14,
            bulletIndent=4,
            spaceAfter=0.8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeX",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=8.8,
            leading=10.8,
            leftIndent=10,
            spaceAfter=0.8,
        )
    )
    return styles


def _normalize_inline(text: str) -> str:
    text = text.replace("`", "")
    chunks = []
    cursor = 0
    for match in LINK_PATTERN.finditer(text):
        if match.start() > cursor:
            chunks.append(escape(text[cursor:match.start()]))
        label = escape(match.group(1))
        href = quoteattr(match.group(2).strip())
        chunks.append(f"<link href={href}>{label}</link>")
        cursor = match.end()
    if cursor < len(text):
        chunks.append(escape(text[cursor:]))
    return "".join(chunks)


def render_markdown_to_pdf(source: Path, target: Path, title: str):
    styles = _styles()
    story = []
    in_code = False
    text = source.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            if line.strip():
                story.append(Paragraph(escape(line), styles["CodeX"]))
            else:
                story.append(Spacer(1, 2))
            continue

        if not line.strip():
            story.append(Spacer(1, 2))
            continue
        if line.startswith("# "):
            story.append(Paragraph(_normalize_inline(line[2:].strip()), styles["H1X"]))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_normalize_inline(line[3:].strip()), styles["H2X"]))
            continue
        if line.startswith("### "):
            story.append(Paragraph(_normalize_inline(line[4:].strip()), styles["H2X"]))
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            story.append(Paragraph(_normalize_inline(stripped[2:]), styles["BulletX"], bulletText="•"))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            numbered = re.sub(r"^\d+\.\s+", "", stripped)
            story.append(Paragraph(_normalize_inline(numbered), styles["BulletX"], bulletText="•"))
            continue
        story.append(Paragraph(_normalize_inline(stripped), styles["BodyX"]))

    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=1.25 * cm,
        rightMargin=1.25 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title=title,
    )
    doc.build(story)


def main():
    for source, target, title in DOC_MAP:
        if not source.exists():
            raise FileNotFoundError(f"Missing source markdown: {source}")
        render_markdown_to_pdf(source, target, title)
        print(f"Generated {target}")


if __name__ == "__main__":
    main()
