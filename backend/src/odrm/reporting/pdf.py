from __future__ import annotations

import io
import textwrap
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)

from odrm.reporting.content import (
    CURRENCY,
    SCHEMA_VERSION,
    ReportData,
    format_optional,
    safe_report_text,
)

_PAGE_WIDTH, _PAGE_HEIGHT = A4
_HORIZONTAL_MARGIN = 18 * mm
_CONTENT_WIDTH = _PAGE_WIDTH - (2 * _HORIZONTAL_MARGIN)
_NAVY = colors.HexColor("#0f2a43")
_BLUE = colors.HexColor("#1d4ed8")
_GREY = colors.HexColor("#4b5563")
_LIGHT_GREY = colors.HexColor("#f3f4f6")
_BORDER = colors.HexColor("#d1d5db")
_WARNING_BG = colors.HexColor("#fff7ed")
_WARNING_BORDER = colors.HexColor("#f97316")
_DISCLAIMER_BG = colors.HexColor("#fef2f2")
_DISCLAIMER_BORDER = colors.HexColor("#b91c1c")


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#111827"),
        spaceAfter=3,
    )
    return {
        "title": ParagraphStyle(
            "title",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=27,
            textColor=_NAVY,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=_BLUE,
            spaceAfter=2,
        ),
        "tagline": ParagraphStyle(
            "tagline",
            parent=base,
            fontSize=9.5,
            leading=13,
            textColor=_GREY,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=_NAVY,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": base,
        "small": ParagraphStyle(
            "small",
            parent=base,
            fontSize=8,
            leading=11,
            textColor=_GREY,
        ),
        "label": ParagraphStyle(
            "label",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=_NAVY,
        ),
        "value": ParagraphStyle(
            "value",
            parent=base,
            fontSize=8.5,
            leading=11.5,
        ),
        "code": ParagraphStyle(
            "code",
            parent=base,
            fontName="Courier",
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor("#111827"),
        ),
        "cell_header": ParagraphStyle(
            "cell_header",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base,
            fontSize=8,
            leading=10.5,
        ),
        "cell_mono": ParagraphStyle(
            "cell_mono",
            parent=base,
            fontName="Courier",
            fontSize=7.2,
            leading=9.5,
        ),
        "disclaimer_title": ParagraphStyle(
            "disclaimer_title",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=_DISCLAIMER_BORDER,
            spaceAfter=5,
        ),
        "disclaimer_body": ParagraphStyle(
            "disclaimer_body",
            parent=base,
            fontSize=8.5,
            leading=11.5,
            spaceAfter=3,
        ),
        "appendix_code": ParagraphStyle(
            "appendix_code",
            parent=base,
            fontName="Courier",
            fontSize=6.3,
            leading=7.6,
            textColor=colors.HexColor("#111827"),
        ),
    }


def _cell(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _table(
    rows: list[list[Any]],
    col_widths: list[float],
    *,
    header: bool = True,
) -> Table:
    table = Table(rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1 if header else 0)
    commands: list[tuple[Any, ...]] = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, _BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT_GREY]),
            ]
        )
    else:
        commands.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT_GREY]))
    table.setStyle(TableStyle(commands))
    return table


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _optional(value: float | str | None, unit: str) -> str:
    if value is None:
        return "Not provided"
    return f"{format_optional(value)} {unit}"


def _section(title: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [Spacer(1, 3), Paragraph(escape(title), styles["section"])]


def _warning_section(report: ReportData, styles: dict[str, ParagraphStyle]) -> list[Any]:
    story = _section("Warnings", styles)
    if not report.warnings:
        story.append(Paragraph("No warnings were generated for this screening.", styles["body"]))
        return story

    rows: list[list[Any]] = [
        [
            Paragraph("Warning", styles["cell_header"]),
            Paragraph("Code", styles["cell_header"]),
        ]
    ]
    for warning in report.warnings:
        rows.append(
            [
                _cell(warning.message, styles["cell"]),
                _cell(warning.code, styles["cell_mono"]),
            ]
        )
    story.append(_table(rows, [_CONTENT_WIDTH * 0.72, _CONTENT_WIDTH * 0.28]))
    return story


def _disclaimer(styles: dict[str, ParagraphStyle]) -> list[Any]:
    story = _section("Important Notice", styles)
    body: list[list[Any]] = [
        [
            Paragraph(
                "IMPORTANT: WHAT THIS REPORT IS AND IS NOT",
                styles["disclaimer_title"],
            )
        ],
        [
            Paragraph(
                "<b>What this is:</b> A preliminary, mathematically accurate screening "
                "estimate to help you determine if your flare gas project is worth pursuing. "
                "It has a cryptographic fingerprint (SHA-256) to ensure the numbers on this "
                "page have not been altered.",
                styles["disclaimer_body"],
            )
        ],
        [Paragraph("<b>What this is NOT:</b>", styles["disclaimer_body"])],
        [
            Paragraph(
                "1. <b>Not a Bankable Audit:</b> A bank will require an independent "
                "engineering firm to verify these numbers before funding your project.",
                styles["disclaimer_body"],
            )
        ],
        [
            Paragraph(
                "2. <b>Not a Verified Carbon Credit:</b> This calculates your potential "
                "carbon savings, but it cannot be sold on international carbon markets "
                "without a multi-year, independent verification audit.",
                styles["disclaimer_body"],
            )
        ],
        [
            Paragraph(
                "3. <b>Not a Blockchain Proof:</b> This is a digital fingerprint of this "
                "specific document, not a blockchain-anchored smart contract.",
                styles["disclaimer_body"],
            )
        ],
    ]
    table = Table(body, colWidths=[_CONTENT_WIDTH], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _DISCLAIMER_BG),
                ("BOX", (0, 0), (-1, -1), 1, _DISCLAIMER_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    return story


def _build_story(report: ReportData, styles: dict[str, ParagraphStyle]) -> list[Any]:
    conditions = report.request.conditions
    assumptions = report.request.assumptions
    financials = report.response.financials
    predictions = report.response.predictions

    story: list[Any] = [
        Paragraph("Valoris ODRM-Copilot", styles["title"]),
        Paragraph("ESG Screening Report", styles["subtitle"]),
        Paragraph("Flare-gas valorization pre-feasibility screening", styles["tagline"]),
    ]

    metadata_rows: list[list[Any]] = [
        [
            _cell("Report ID", styles["label"]),
            _cell(report.report_id, styles["code"]),
        ],
        [
            _cell("Generated at (UTC)", styles["label"]),
            _cell(report.generated_at, styles["value"]),
        ],
        [
            _cell("Report schema version", styles["label"]),
            _cell(report.schema_version, styles["code"]),
        ],
        [
            _cell("Currency", styles["label"]),
            _cell(CURRENCY, styles["value"]),
        ],
        [
            _cell("SHA-256 integrity digest", styles["label"]),
            _cell(report.sha256, styles["code"]),
        ],
    ]
    story.append(_table(metadata_rows, [_CONTENT_WIDTH * 0.28, _CONTENT_WIDTH * 0.72]))
    story.append(
        Paragraph(
            "SHA-256 integrity digest of the canonical audit payload. This is a "
            "tamper-evident checksum of the underlying data, not a digital signature, "
            "blockchain anchor, or proof of carbon-credit ownership.",
            styles["small"],
        )
    )

    payback = (
        "Not available"
        if financials.payback_years is None
        else f"{financials.payback_years:.2f} years"
    )
    story.extend(_section("Executive Summary", styles))
    kpi_rows: list[list[Any]] = [
        [
            Paragraph("Metric", styles["cell_header"]),
            Paragraph("Value", styles["cell_header"]),
        ],
        [_cell("CH4 conversion", styles["cell"]), _cell(f"{predictions['ch4_conversion'] * 100:.2f}%", styles["cell"])],
        [
            _cell("Syngas yield", styles["cell"]),
            _cell(f"{predictions['syngas_yield_mol_per_mol_ch4']:.2f} mol/mol CH4", styles["cell"]),
        ],
        [
            _cell("Annual net cash flow", styles["cell"]),
            _cell(f"{_usd(financials.annual_net_cash_flow_usd)} / year", styles["cell"]),
        ],
        [_cell("ROI", styles["cell"]), _cell(f"{financials.roi_pct:.2f}%", styles["cell"])],
        [_cell("Payback period", styles["cell"]), _cell(payback, styles["cell"])],
    ]
    story.append(_table(kpi_rows, [_CONTENT_WIDTH * 0.45, _CONTENT_WIDTH * 0.55]))
    story.extend(
        [
            Paragraph("Plant and Reactor Conditions", styles["section"]),
            _table(
                [
                    [_cell("Parameter", styles["label"]), _cell("Value", styles["label"])],
                    [
                        _cell("Temperature", styles["cell"]),
                        _cell(f"{conditions.temperature_c:.1f} deg C", styles["cell"]),
                    ],
                    [
                        _cell("Pressure", styles["cell"]),
                        _cell(f"{conditions.pressure_bar:.2f} bar", styles["cell"]),
                    ],
                    [_cell("CH4/O2 ratio", styles["cell"]), _cell(f"{conditions.ch4_o2_ratio:.2f}", styles["cell"])],
                    [_cell("CO2/CH4 ratio", styles["cell"]), _cell(f"{conditions.co2_ch4_ratio:.2f}", styles["cell"])],
                    [_cell("H2O/CH4 ratio", styles["cell"]), _cell(f"{conditions.h2o_ch4_ratio:.2f}", styles["cell"])],
                    [_cell("GHSV", styles["cell"]), _cell(f"{conditions.ghsv_per_h:,.0f} 1/h", styles["cell"])],
                    [
                        _cell("Catalyst", styles["cell"]),
                        _cell(safe_report_text(conditions.catalyst, max_length=80), styles["cell"]),
                    ],
                    [
                        _cell("Catalyst loading", styles["cell"]),
                        _cell(_optional(conditions.catalyst_loading_wt_pct, "wt%"), styles["cell"]),
                    ],
                    [
                        _cell("N2 dilution", styles["cell"]),
                        _cell(_optional(conditions.n2_dilution_mol_pct, "mol%"), styles["cell"]),
                    ],
                ],
                [_CONTENT_WIDTH * 0.45, _CONTENT_WIDTH * 0.55],
            ),
        ]
    )

    story.extend(_section("AI Predictions and Provenance", styles))
    prediction_rows: list[list[Any]] = [
        [
            Paragraph("Target", styles["cell_header"]),
            Paragraph("Predicted value", styles["cell_header"]),
            Paragraph("Model version", styles["cell_header"]),
        ],
        [
            _cell("CH4 conversion", styles["cell"]),
            _cell(f"{predictions['ch4_conversion'] * 100:.2f}%", styles["cell"]),
            _cell(report.response.model_versions["ch4_conversion"], styles["cell_mono"]),
        ],
        [
            _cell("Syngas yield", styles["cell"]),
            _cell(f"{predictions['syngas_yield_mol_per_mol_ch4']:.2f} mol/mol CH4", styles["cell"]),
            _cell(
                report.response.model_versions["syngas_yield_mol_per_mol_ch4"],
                styles["cell_mono"],
            ),
        ],
    ]
    story.append(_table(prediction_rows, [_CONTENT_WIDTH * 0.3, _CONTENT_WIDTH * 0.4, _CONTENT_WIDTH * 0.3]))
    story.append(
        Paragraph(
            "These predictions come from the pinned surrogate models listed above and are "
            "not LLM-generated.",
            styles["body"],
        )
    )

    story.extend(_section("Financial Screening", styles))
    financial_rows: list[list[Any]] = [
        [
            Paragraph("Metric", styles["cell_header"]),
            Paragraph("Value", styles["cell_header"]),
        ],
        [
            _cell("Syngas production", styles["cell"]),
            _cell(
                f"{financials.syngas_kmol_per_day:,.2f} kmol/day "
                f"({financials.syngas_nm3_per_day:,.2f} Nm3/day)",
                styles["cell"],
            ),
        ],
        [
            _cell("Syngas revenue", styles["cell"]),
            _cell(f"{_usd(financials.syngas_revenue_usd_per_day)} / day", styles["cell"]),
        ],
        [
            _cell("CO2 consumed", styles["cell"]),
            _cell(f"{financials.co2_consumed_tonnes_per_day:,.4f} tonnes/day", styles["cell"]),
        ],
        [
            _cell("Carbon-credit value", styles["cell"]),
            _cell(f"{_usd(financials.carbon_credit_value_usd_per_day)} / day", styles["cell"]),
        ],
        [
            _cell("Total revenue", styles["cell"]),
            _cell(f"{_usd(financials.total_revenue_usd_per_day)} / day", styles["cell"]),
        ],
        [
            _cell("Feed cost", styles["cell"]),
            _cell(f"{_usd(financials.feed_cost_usd_per_day)} / day", styles["cell"]),
        ],
        [
            _cell("OPEX", styles["cell"]),
            _cell(f"{_usd(financials.opex_usd_per_day)} / day", styles["cell"]),
        ],
        [
            _cell("Net cash flow", styles["cell"]),
            _cell(f"{_usd(financials.net_cash_flow_usd_per_day)} / day", styles["cell"]),
        ],
        [
            _cell("Annual net cash flow", styles["cell"]),
            _cell(f"{_usd(financials.annual_net_cash_flow_usd)} / year", styles["cell"]),
        ],
        [_cell("ROI", styles["cell"]), _cell(f"{financials.roi_pct:.2f}%", styles["cell"])],
        [_cell("Payback period", styles["cell"]), _cell(payback, styles["cell"])],
    ]
    story.append(_table(financial_rows, [_CONTENT_WIDTH * 0.45, _CONTENT_WIDTH * 0.55]))

    story.extend(_section("Assumptions Used", styles))
    assumption_rows: list[list[Any]] = [
        [_cell("Assumption", styles["cell_header"]), _cell("Value", styles["cell_header"])],
        [_cell("CH4 feed rate", styles["cell"]), _cell(f"{assumptions.ch4_feed_kmol_per_h:,.2f} kmol/h", styles["cell"])],
        [
            _cell("Natural-gas price", styles["cell"]),
            _cell(f"{_usd(assumptions.natural_gas_price_usd_per_mmbtu)} / MMBtu", styles["cell"]),
        ],
        [
            _cell("Syngas price", styles["cell"]),
            _cell(f"{_usd(assumptions.syngas_price_usd_per_kmol)} / kmol", styles["cell"]),
        ],
        [
            _cell("Carbon-credit price", styles["cell"]),
            _cell(f"{_usd(assumptions.carbon_credit_price_usd_per_tonne_co2e)} / tonne CO2e", styles["cell"]),
        ],
        [
            _cell("CO2 utilization fraction", styles["cell"]),
            _cell(f"{assumptions.co2_utilization_fraction * 100:.2f}%", styles["cell"]),
        ],
        [_cell("CAPEX", styles["cell"]), _cell(_usd(assumptions.capex_usd), styles["cell"])],
        [
            _cell("OPEX", styles["cell"]),
            _cell(f"{assumptions.opex_pct_of_capex_per_year:.2f}% of CAPEX / year", styles["cell"]),
        ],
        [
            _cell("Operating hours", styles["cell"]),
            _cell(f"{assumptions.operating_hours_per_day:.1f} h/day", styles["cell"]),
        ],
        [
            _cell("Operating days", styles["cell"]),
            _cell(f"{assumptions.operating_days_per_year:.1f} days/year", styles["cell"]),
        ],
    ]
    story.append(_table(assumption_rows, [_CONTENT_WIDTH * 0.45, _CONTENT_WIDTH * 0.55]))

    story.extend(_warning_section(report, styles))

    story.extend(_section("Methodology and Limitations", styles))
    story.append(
        Paragraph(
            "The predictions come from surrogate models trained on synthetic ODRM data and "
            "provide screening-level estimates. This report is not a bankable feasibility "
            "study, an audited financial statement, or a verified carbon credit. Values "
            "depend on the supplied assumptions and market prices at the time of input. No "
            "warranty is provided; engineering review is required before capital commitment.",
            styles["body"],
        )
    )

    story.extend(_disclaimer(styles))

    story.append(PageBreak())
    story.extend(_section("Integrity Appendix", styles))
    story.append(
        Paragraph(
            "Canonical audit payload below. The SHA-256 digest in the report metadata is "
            "computed over the UTF-8 bytes of this canonical form, with sorted keys and "
            "compact separators. The JSON is wrapped here for display only; line breaks are "
            "not part of the payload.",
            styles["body"],
        )
    )
    wrapped_lines = textwrap.wrap(
        report.canonical_payload,
        width=112,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    )
    story.append(
        XPreformatted(
            escape("\n".join(wrapped_lines)),
            styles["appendix_code"],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Recompute SHA-256 over the exact canonical JSON (joining the wrapped lines "
            "without inserting spaces) and compare it to the printed digest.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"Report ID: {escape(report.report_id)} | Generated at: "
            f"{escape(report.generated_at)} | Schema: {escape(SCHEMA_VERSION)}",
            styles["small"],
        )
    )

    return story


def _decorate_page(canvas: Any, doc: Any, report_id: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(_BORDER)
    canvas.setLineWidth(0.5)
    canvas.setFillColor(_GREY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(_HORIZONTAL_MARGIN, _PAGE_HEIGHT - 12 * mm, "Valoris ODRM-Copilot")
    canvas.drawRightString(
        _PAGE_WIDTH - _HORIZONTAL_MARGIN,
        _PAGE_HEIGHT - 12 * mm,
        f"ESG Screening Report | {report_id}",
    )
    canvas.line(
        _HORIZONTAL_MARGIN,
        _PAGE_HEIGHT - 14 * mm,
        _PAGE_WIDTH - _HORIZONTAL_MARGIN,
        _PAGE_HEIGHT - 14 * mm,
    )
    canvas.drawString(_HORIZONTAL_MARGIN, 10 * mm, "ODRM-Copilot ESG Screening Report")
    canvas.drawRightString(
        _PAGE_WIDTH - _HORIZONTAL_MARGIN,
        10 * mm,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.line(
        _HORIZONTAL_MARGIN,
        13 * mm,
        _PAGE_WIDTH - _HORIZONTAL_MARGIN,
        13 * mm,
    )
    canvas.restoreState()


def render_pdf(report: ReportData) -> bytes:
    buffer = io.BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=_HORIZONTAL_MARGIN,
        rightMargin=_HORIZONTAL_MARGIN,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="ODRM-Copilot ESG Screening Report",
        author="Valoris ODRM-Copilot",
        subject="Flare-gas valorization pre-feasibility screening",
        creator="ODRM-Copilot",
    )
    doc.build(
        _build_story(report, styles),
        onFirstPage=lambda canvas, doc: _decorate_page(canvas, doc, report.report_id),
        onLaterPages=lambda canvas, doc: _decorate_page(canvas, doc, report.report_id),
    )
    return buffer.getvalue()
