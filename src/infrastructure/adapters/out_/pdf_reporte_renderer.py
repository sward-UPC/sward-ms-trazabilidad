"""Renderer PDF del reporte de clase usando reportlab (platypus).

Produce un PDF profesional: cabecera SWARD, metadatos, tarjeta de resumen por
nivel de riesgo y tabla detallada por estudiante con código de color de riesgo.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.application.use_cases.generar_reporte_docente import ReporteClase
from src.domain.ports.out_.reporte_renderer_port import ReporteRendererPort
from src.domain.value_objects.nivel_riesgo import NivelRiesgo

# Paleta SWARD.
_AZUL = colors.HexColor("#1565c0")
_GRIS_FONDO = colors.HexColor("#f4f9ff")
_GRIS_BORDE = colors.HexColor("#cfd8dc")
_FILA_ALT = colors.HexColor("#eef4fb")

# Color por nivel de riesgo.
_COLOR_RIESGO = {
    NivelRiesgo.CRITICO: colors.HexColor("#c62828"),
    NivelRiesgo.ALTO: colors.HexColor("#ef6c00"),
    NivelRiesgo.MEDIO: colors.HexColor("#f9a825"),
    NivelRiesgo.BAJO: colors.HexColor("#2e7d32"),
}
_LABEL_RIESGO = {
    NivelRiesgo.CRITICO: "Crítico",
    NivelRiesgo.ALTO: "Alto",
    NivelRiesgo.MEDIO: "Medio",
    NivelRiesgo.BAJO: "Bajo",
}
# Hex para colorear el texto dentro de Paragraphs (TableStyle TEXTCOLOR no aplica
# sobre celdas que son Paragraph).
_HEX_RIESGO = {
    NivelRiesgo.CRITICO: "#c62828",
    NivelRiesgo.ALTO: "#ef6c00",
    NivelRiesgo.MEDIO: "#f9a825",
    NivelRiesgo.BAJO: "#2e7d32",
}


class PdfReporteRenderer(ReporteRendererPort):
    def render(self, reporte: ReporteClase) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            title="Reporte de Progreso de Clase — SWARD",
            author="SWARD",
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle(
            "SwardTitle",
            parent=styles["Title"],
            textColor=_AZUL,
            fontSize=20,
            spaceAfter=2,
        )
        sub = ParagraphStyle(
            "SwardSub",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#546e7a"),
            alignment=TA_LEFT,
        )
        meta = ParagraphStyle(
            "SwardMeta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#78909c"),
        )
        section = ParagraphStyle(
            "SwardSection",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=_AZUL,
            spaceBefore=10,
            spaceAfter=6,
        )

        fecha = reporte.generado_en.strftime("%d/%m/%Y %H:%M UTC")
        elems = [
            Paragraph("SWARD", h1),
            Paragraph("Reporte de Progreso de Clase — Trazabilidad Docente", sub),
            Spacer(1, 4),
            Paragraph(f"Curso: <b>{reporte.curso_id}</b>", meta),
            Paragraph(f"Generado: {fecha}", meta),
            Spacer(1, 10),
        ]

        # ── Resumen ──────────────────────────────────────────────
        elems.append(Paragraph("Resumen", section))
        resumen_data = [
            ["Total", "Crítico", "Alto", "Medio", "Bajo", "Dominio prom."],
            [
                str(reporte.total),
                str(reporte.criticos),
                str(reporte.altos),
                str(reporte.medios),
                str(reporte.bajos),
                f"{reporte.promedio_dominio:.1f}%",
            ],
        ]
        resumen = Table(resumen_data, colWidths=[None] * 6)
        resumen.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 1), (-1, 1), _GRIS_FONDO),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, _GRIS_BORDE),
                    ("TEXTCOLOR", (1, 1), (1, 1), _COLOR_RIESGO[NivelRiesgo.CRITICO]),
                    ("TEXTCOLOR", (2, 1), (2, 1), _COLOR_RIESGO[NivelRiesgo.ALTO]),
                    ("FONTNAME", (1, 1), (2, 1), "Helvetica-Bold"),
                ]
            )
        )
        elems.append(resumen)
        elems.append(Spacer(1, 14))

        # ── Detalle por estudiante ───────────────────────────────
        elems.append(Paragraph("Detalle por estudiante", section))
        cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9)
        cell_c = ParagraphStyle("CellC", parent=cell, alignment=TA_CENTER)
        encabezado = [
            Paragraph("<b>#</b>", cell_c),
            Paragraph("<b>Estudiante</b>", cell),
            Paragraph("<b>Correo</b>", cell),
            Paragraph("<b>Riesgo</b>", cell_c),
            Paragraph("<b>Dominio</b>", cell_c),
            Paragraph("<b>Interac.</b>", cell_c),
            Paragraph("<b>Recursos</b>", cell_c),
        ]
        filas = [encabezado]
        for i, e in enumerate(reporte.estudiantes, start=1):
            nivel = e.progreso.nivel_riesgo
            nombre = (f"{e.nombre} {e.apellido}".strip()) or e.correo or "—"
            label = _LABEL_RIESGO.get(nivel, str(nivel))
            hexcol = _HEX_RIESGO.get(nivel, "#000000")
            filas.append(
                [
                    Paragraph(str(i), cell_c),
                    Paragraph(nombre, cell),
                    Paragraph(e.correo or "—", cell),
                    Paragraph(f'<font color="{hexcol}"><b>{label}</b></font>', cell_c),
                    Paragraph(f"{e.progreso.puntaje_promedio:.0f}%", cell_c),
                    Paragraph(str(e.progreso.total_interacciones), cell_c),
                    Paragraph(str(e.progreso.recursos_completados), cell_c),
                ]
            )

        tabla = Table(
            filas,
            colWidths=[10 * mm, 42 * mm, 50 * mm, 20 * mm, 18 * mm, 18 * mm, 20 * mm],
            repeatRows=1,
        )
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_BORDE),
        ]
        for r in range(1, len(filas)):
            if r % 2 == 0:
                estilo.append(("BACKGROUND", (0, r), (-1, r), _FILA_ALT))
        tabla.setStyle(TableStyle(estilo))
        elems.append(tabla)

        elems.append(Spacer(1, 16))
        elems.append(
            Paragraph(
                "Generado automáticamente por SWARD · Sistema Web de Recomendación "
                "Adaptativa y Distribuida.",
                ParagraphStyle(
                    "Footer",
                    parent=styles["Normal"],
                    fontSize=8,
                    textColor=colors.HexColor("#90a4ae"),
                    alignment=TA_CENTER,
                ),
            )
        )

        doc.build(elems)
        return buffer.getvalue()
