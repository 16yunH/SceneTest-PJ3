#!/usr/bin/env python3
"""Generate the English PDF report and a LaTeX source draft."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from textwrap import dedent

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "experiments" / "runs" / "batch"
OUT_DIR = ROOT / "deliverables" / "report"
ASSET_DIR = ROOT / "deliverables" / "assets"
AUTHOR_EN = os.environ.get("SCENETEST_AUTHOR_EN", "Your Name")
STUDENT_ID = os.environ.get("SCENETEST_STUDENT_ID", "Student ID")
CODE_URL = os.environ.get("SCENETEST_CODE_URL", "https://github.com/<your-github-user>/SceneTest-PJ3")


def load_results() -> list[dict[str, str]]:
    with (RUN_DIR / "results.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def metric_rate(rows: list[dict[str, str]], method: str, metric: str) -> float:
    for row in rows:
        if row["method"] == method and row["metric"] == metric:
            return float(row["rate"])
    raise KeyError((method, metric))


def method_table(rows: list[dict[str, str]]) -> list[list[str]]:
    metrics = [
        "Object Completeness",
        "Spatial Relation Accuracy",
        "Visibility Pass Rate",
        "Lighting Pass Rate",
        "Overall Contract Pass Rate",
    ]
    methods = ["single_pass", "contract_only", "scenetest"]
    table = [["Metric", "Single-pass", "Contract-only", "SceneTest"]]
    for metric in metrics:
        table.append([metric] + [f"{100 * metric_rate(rows, method, metric):.1f}%" for method in methods])
    return table


def test_case_table(scene_id: str) -> list[list[str]]:
    data = []
    for method, label in [("contract_only", "Initial"), ("scenetest", "SceneTest")]:
        results = json.loads((RUN_DIR / scene_id / method / "test_results.json").read_text(encoding="utf-8"))
        total = len(results)
        passed = sum(1 for item in results if item["status"] == "pass")
        failures = [item["name"] for item in results if item["status"] != "pass"]
        data.append([label, f"{passed}/{total}", ", ".join(failures[:4]) or "None"])
    return [["Version", "Passed tests", "Representative failures"], *data]


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.strip().replace("\n", "<br/>"), style)


def build_pdf() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUT_DIR / "SceneTest_report.pdf"
    rows = load_results()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=18,
    )
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=15, leading=19, spaceBefore=12, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, leading=15, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.4, leading=13, alignment=TA_LEFT, spaceAfter=6)
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=10, textColor=colors.HexColor("#4B5563"))
    code = ParagraphStyle("Code", parent=body, fontName="Courier", fontSize=7.6, leading=9.5, backColor=colors.HexColor("#F4F4F5"), borderPadding=5)

    story: list[object] = []
    story.append(Paragraph("SceneTest: Contract-Driven Graphics Unit Tests for Agentic Text-to-3D Scene Generation", title_style))
    story.append(
        Paragraph(
            "Computer Graphics Project 3, Spring 2026<br/>"
            f"Code: {CODE_URL}",
            subtitle_style,
        )
    )
    story.append(Paragraph("Abstract", h1))
    story.append(
        para(
            """
            Large language models can generate Blender Python code from natural language, but direct
            text-to-code scene generation often misses objects, violates spatial relations, or places
            objects outside the camera view. SceneTest converts a prompt into a structured Scene
            Contract, compiles the contract into executable graphics unit tests, and uses failed tests
            to guide localized repairs of the generated scene. The prototype implements a deterministic
            contract parser, a constrained scene-builder API, object/relation/material/lighting/visibility
            tests, and repair rules that create missing objects, move objects according to failed
            relations, fix appearance constraints, and auto-frame the camera. On a 20-prompt benchmark
            with 311 generated tests, SceneTest improves overall contract pass rate from 67.2% for a
            single-pass baseline and 79.1% for a contract-only baseline to 100.0% after repair.
            """,
            body,
        )
    )

    story.append(Paragraph("1. Introduction", h1))
    story.append(
        para(
            """
            Agentic text-to-3D generation can be framed as code generation: an agent interprets a prompt,
            writes Blender Python, executes the script, and optionally refines the result. This workflow is
            attractive because generated code is inspectable and editable, yet it is also fragile. A visually
            plausible scene can still fail explicit prompt requirements, such as placing a cup on the wrong
            side of a laptop or creating a plant that exists in the object registry but is not visible to the
            camera. SceneTest treats these failures as test failures rather than vague visual feedback.
            """,
            body,
        )
    )
    story.append(
        para(
            """
            The central idea is to introduce a contract-driven layer between the prompt and the scene code.
            The contract names required objects, spatial relations, appearance requirements, lighting style,
            and visible objects. From that contract, the system compiles graphics unit tests that can be run
            on scene state. Failed tests then map to deterministic local repairs.
            """,
            body,
        )
    )

    story.append(Paragraph("2. Related Work", h1))
    story.append(
        para(
            """
            The project is related to LLM-based 3D generation systems such as LL3M and SceneCraft, agentic
            3D scene generation systems such as SAGE, and code repair systems that use execution feedback.
            Prior work often uses visual reflection or whole-program regeneration. SceneTest instead adds
            an explicit graphics testing layer, inspired by software unit testing, that converts prompt
            requirements into measurable 3D constraints.
            """,
            body,
        )
    )

    story.append(Paragraph("3. Method", h1))
    story.append(Paragraph("3.1 Scene Contract", h2))
    story.append(
        para(
            """
            A Scene Contract is a JSON representation of prompt requirements. It contains required objects,
            stable object identifiers, object types, material/color attributes, spatial relations, lighting
            style, and camera visibility targets.
            """,
            body,
        )
    )
    story.append(
        Paragraph(
            dedent(
                """
                {
                  "objects": ["desk", "laptop", "lamp", "coffee_cup", "plant"],
                  "relations": [
                    {"subject": "laptop", "relation": "on", "object": "desk"},
                    {"subject": "lamp", "relation": "left_of", "object": "laptop"},
                    {"subject": "coffee_cup", "relation": "right_of", "object": "laptop"}
                  ],
                  "style": {"lighting": "warm"},
                  "camera": {"visible_objects": ["desk", "laptop", "lamp", "coffee_cup", "plant"]}
                }
                """
            ),
            code,
        )
    )
    story.append(Paragraph("3.2 Graphics Unit Tests", h2))
    story.append(
        para(
            """
            Tests are compiled deterministically. Object tests inspect the scene registry. Geometry tests use
            world-space bounding boxes. Visibility tests approximate camera projection with the camera frame.
            Appearance tests inspect material/color metadata and lighting tests inspect the scene lighting
            style. This is a lightweight backend, but every test corresponds to a graphics concept that can
            be implemented in Blender using object registries, bounding boxes, material nodes, lights, and
            camera projection.
            """,
            body,
        )
    )
    story.append(Paragraph("3.3 Failure-Guided Repair", h2))
    story.append(
        para(
            """
            Each failed test produces a structured repair hint. For example, a failed right_of relation maps
            to a local transform update that moves the subject object to the positive x side of the target.
            A failed on relation sets the subject bottom z value to the target top z value and centers the
            subject over the support. Visibility failures trigger camera auto-framing over required objects.
            The repair loop is bounded to three iterations.
            """,
            body,
        )
    )

    story.append(Paragraph("4. Implementation", h1))
    story.append(
        para(
            """
            The prototype is implemented as a Python package with no required external API key. The Contract
            Agent is deterministic for reproducibility, the Code Agent emits constrained SceneBuilder API
            calls, the Test Runner executes generated scene programs in an in-memory backend, and the Blender
            exporter writes optional Blender Python scripts. If Blender is installed, the generated
            scene.blender.py files can be rendered directly; otherwise, the project still produces top-down
            PNG/SVG previews for reports and slides.
            """,
            body,
        )
    )

    story.append(Paragraph("5. Experiments", h1))
    story.append(
        para(
            """
            We evaluate 20 prompts spanning desk scenes, living rooms, geometric arrangements, and stylized
            setups. The evaluation compares three methods: Single-pass, Contract-only, and SceneTest.
            Single-pass simulates unconstrained prompt-to-scene generation with omitted objects and relation
            mistakes. Contract-only uses the contract and helper API but does not repair failed tests.
            SceneTest runs the same initial contract-only scene through graphics unit tests and repairs.
            """,
            body,
        )
    )
    story.append(_styled_table(method_table(rows), col_widths=[2.1 * inch, 1.15 * inch, 1.15 * inch, 1.15 * inch]))
    story.append(Spacer(1, 8))
    story.append(
        para(
            """
            The benchmark generated 93 object tests, 73 spatial relation tests, 93 visibility tests, 10 color
            tests, 2 material tests, and 20 lighting tests. SceneTest reached 311/311 passing tests after
            repair.
            """,
            small,
        )
    )

    story.append(Paragraph("6. Qualitative Case Study", h1))
    story.append(
        para(
            """
            In the cozy desk scene, the initial contract-only generation places the cup on the wrong side
            and may use neutral lighting. The failure report maps these issues to a move_relation action and
            a set_lighting action. After repair, all required objects satisfy the contract and the camera
            frame contains every target object.
            """,
            body,
        )
    )
    story.append(_styled_table(test_case_table("desk_cozy"), col_widths=[1.0 * inch, 1.0 * inch, 4.2 * inch]))
    story.append(Spacer(1, 8))
    story.append(
        _image_pair(
            RUN_DIR / "desk_cozy" / "contract_only" / "render.png",
            RUN_DIR / "desk_cozy" / "scenetest" / "render.png",
            "Before repair",
            "After SceneTest repair",
            small,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("7. Ablation and Limitations", h1))
    story.append(
        para(
            """
            Relation tests are the most important source of improvement: the contract-only relation pass
            rate is 64.4%, while repaired SceneTest reaches 100.0%. Visibility tests expose a different
            failure mode: objects may exist and satisfy relations but fall outside the camera frame. The
            current prototype uses bounding-box and top-down camera approximations, so future work should
            implement Blender segmentation masks and occlusion-aware visibility. The deterministic parser is
            intentionally conservative and should be replaced or augmented by an LLM contract agent for
            open-vocabulary scenes.
            """,
            body,
        )
    )

    story.append(Paragraph("8. Conclusion", h1))
    story.append(
        para(
            """
            SceneTest demonstrates that agentic text-to-3D generation can benefit from a test-driven graphics
            loop. The project contributes a shared Scene Contract representation, executable Graphics Unit
            Tests for 3D scene requirements, and deterministic Failure-Guided Repair rules that improve
            prompt alignment without whole-scene regeneration.
            """,
            body,
        )
    )

    story.append(Paragraph("References", h1))
    refs = [
        "Blender Foundation. Blender Python API Documentation. https://docs.blender.org/api/current/",
        "Lu et al. LL3M: Large Language 3D Modelers. arXiv, 2025.",
        "Xia et al. SAGE: Scalable Agentic 3D Scene Generation for Embodied AI. arXiv, 2026.",
        "Morris et al. Levels of AGI for Operationalizing Progress on the Path to AGI. ICML, 2024.",
        "Course Project 3 slides, 2026 Spring Computer Graphics.",
    ]
    for ref in refs:
        story.append(para(ref, small))

    story.append(Paragraph("Appendix: Member Contributions", h1))
    story.append(
        para(
            f"""
            {AUTHOR_EN} / {STUDENT_ID}: project design, Scene Contract schema, Contract Agent and DeepSeek integration,
            helper-API scene builder, graphics unit tests, repair loop, Blender renderer, benchmark execution,
            live demo interface, report, and presentation.
            """,
            body,
        )
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="SceneTest Report",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return pdf_path


def _styled_table(data: list[list[str]], col_widths: list[float]) -> Table:
    table_data = [[Paragraph(cell, getSampleStyleSheet()["BodyText"]) for cell in row] for row in data]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _image_pair(left: Path, right: Path, left_label: str, right_label: str, style: ParagraphStyle) -> KeepTogether:
    images = []
    for path, label in [(left, left_label), (right, right_label)]:
        img = Image(str(path), width=2.85 * inch, height=2.02 * inch)
        images.append([img, Paragraph(label, style)])
    table = Table(
        [
            [images[0][0], images[1][0]],
            [images[0][1], images[1][1]],
        ],
        colWidths=[3.0 * inch, 3.0 * inch],
    )
    table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return KeepTogether([table])


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(0.72 * inch, 0.35 * inch, "SceneTest - Computer Graphics Project 3")
    canvas.drawRightString(7.8 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_tex() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = OUT_DIR / "main.tex"
    rows = load_results()
    tex = rf"""
\documentclass{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{booktabs}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\title{{SceneTest: Contract-Driven Graphics Unit Tests for Agentic Text-to-3D Scene Generation}}
\author{{Computer Graphics Project 3\\\\Spring 2026\\\\{AUTHOR_EN} \\quad Student ID: {STUDENT_ID}}}
\date{{Spring 2026}}
\begin{{document}}
\maketitle
\begin{{abstract}}
SceneTest converts a natural-language 3D scene prompt into a structured Scene Contract,
compiles the contract into executable graphics unit tests, and uses failed tests to guide
localized repairs. On a 20-prompt benchmark with 311 generated tests, SceneTest improves
overall contract pass rate from {100*metric_rate(rows, "single_pass", "Overall Contract Pass Rate"):.1f}\%
for a single-pass baseline and {100*metric_rate(rows, "contract_only", "Overall Contract Pass Rate"):.1f}\%
for a contract-only baseline to {100*metric_rate(rows, "scenetest", "Overall Contract Pass Rate"):.1f}\%.
Code: \url{{{CODE_URL}}}.
\end{{abstract}}
\section{{Method}}
SceneTest introduces a Scene Contract, Graphics Unit Tests, and Failure-Guided Repair.
\section{{Results}}
\begin{{tabular}}{{lccc}}
\toprule
Metric & Single-pass & Contract-only & SceneTest\\
\midrule
Overall pass rate & {100*metric_rate(rows, "single_pass", "Overall Contract Pass Rate"):.1f}\% & {100*metric_rate(rows, "contract_only", "Overall Contract Pass Rate"):.1f}\% & {100*metric_rate(rows, "scenetest", "Overall Contract Pass Rate"):.1f}\%\\
Relation accuracy & {100*metric_rate(rows, "single_pass", "Spatial Relation Accuracy"):.1f}\% & {100*metric_rate(rows, "contract_only", "Spatial Relation Accuracy"):.1f}\% & {100*metric_rate(rows, "scenetest", "Spatial Relation Accuracy"):.1f}\%\\
Visibility pass rate & {100*metric_rate(rows, "single_pass", "Visibility Pass Rate"):.1f}\% & {100*metric_rate(rows, "contract_only", "Visibility Pass Rate"):.1f}\% & {100*metric_rate(rows, "scenetest", "Visibility Pass Rate"):.1f}\%\\
\bottomrule
\end{{tabular}}
\section{{Member Contributions}}
{AUTHOR_EN} / {STUDENT_ID}: project design, Scene Contract schema, Contract Agent and DeepSeek integration, helper-API scene builder, graphics unit tests, repair loop, Blender renderer, benchmark execution, live demo interface, report, and presentation.
\end{{document}}
"""
    tex_path.write_text(tex.strip() + "\n", encoding="utf-8")
    return tex_path


def main() -> None:
    pdf = build_pdf()
    tex = build_tex()
    print(f"Wrote {pdf}")
    print(f"Wrote {tex}")


if __name__ == "__main__":
    main()
