from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .paths import get_exports_dir
from .reports import generate_weekly_report


def generate_weekly_pdf(week_start: str) -> tuple[str, str]:
    start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
    end_date = start_date + timedelta(days=6)
    week_end = end_date.isoformat()
    report = generate_weekly_report(week_start, week_end)

    reports_dir = get_exports_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"routine_report_{week_start}_{week_end}.pdf"
    path = reports_dir / filename
    _build_pdf(path, week_start, week_end, report)
    return str(path), filename


def _build_pdf(path: Path, week_start: str, week_end: str, report: dict) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Routine IA - Relatorio {week_start}",
    )
    story = [
        Paragraph("Routine IA - Relatorio semanal", styles["Title"]),
        Paragraph(f"Periodo: {week_start} a {week_end}", styles["Normal"]),
        Spacer(1, 0.35 * cm),
    ]

    metrics = report["metrics"]
    table_data = [
        ["Metrica", "Valor"],
        ["Pontuacao media", f"{metrics['average_score']:.1f}"],
        ["Sono medio", f"{metrics['average_sleep']:.1f}h"],
        ["Energia/Humor", f"{metrics['average_energy']:.1f} / {metrics['average_mood']:.1f}"],
        ["Alimentacao", f"{metrics['nutrition_average']:.1f}"],
        ["Agua media", f"{metrics['water_average']:.1f}L"],
        ["Foco", f"{metrics['focus_sessions']} sessoes / {metrics['focus_hours']:.1f}h"],
    ]
    if "load_index" in metrics:
        table_data.append(["Carga da semana", f"{metrics['load_index']}/100"])
    if "habits_completed" in metrics:
        table_data.append(["Habitos", f"{metrics['habits_completed']} conclusoes"])
    if "study_session_hours" in metrics:
        table_data.append(["Estudos por sessoes", f"{metrics['study_session_hours']:.1f}h / {metrics.get('study_accuracy', 0):.1f}%"])
    if "life_goals_active" in metrics:
        table_data.append(["Objetivos ativos", f"{metrics['life_goals_active']}"])
    if "active_alerts" in metrics:
        table_data.append(["Alertas ativos", f"{metrics['active_alerts']}"])
    if "pc_total_minutes" in metrics:
        table_data.append(["Uso do PC", f"{metrics['pc_total_minutes']:.0f}min total"])
        table_data.append(["PC produtivo", f"{metrics.get('pc_productive_minutes', 0):.0f}min"])
        table_data.append(["PC distracao", f"{metrics.get('pc_distraction_minutes', 0):.0f}min"])
    story.append(_table(table_data))
    story.append(Spacer(1, 0.35 * cm))

    if report.get("project_hours"):
        project_rows = [["Projeto", "Horas"]]
        project_rows.extend([[name, f"{hours:.1f}h"] for name, hours in report["project_hours"].items()])
        story.append(Paragraph("Projetos", styles["Heading2"]))
        story.append(_table(project_rows))
        story.append(Spacer(1, 0.35 * cm))


    if report.get("app_usage"):
        usage = report["app_usage"]
        story.append(Paragraph("Uso do PC", styles["Heading2"]))
        usage_rows = [["Item", "Tempo"]]
        usage_rows.append(["Total monitorado", f"{usage.get('total_minutes', 0):.0f}min"])
        usage_rows.append(["Produtivo", f"{usage.get('productive_minutes', 0):.0f}min"])
        usage_rows.append(["Neutro", f"{usage.get('neutral_minutes', 0):.0f}min"])
        usage_rows.append(["Distracao", f"{usage.get('distraction_minutes', 0):.0f}min"])
        for item in usage.get("by_app", [])[:5]:
            usage_rows.append([f"App: {item['label']}", f"{item['minutes']:.0f}min"])
        for item in usage.get("by_category", [])[:4]:
            usage_rows.append([f"Categoria: {item['label']}", f"{item['minutes']:.0f}min"])
        if len(usage_rows) == 5 and not usage.get("total_seconds"):
            usage_rows.append(["Sem dados", "0min"])
        story.append(_table(usage_rows))
        story.append(Spacer(1, 0.35 * cm))

    story.append(Paragraph("Analise", styles["Heading2"]))
    for insight in report["insights"]:
        story.append(Paragraph(f"- {insight}", styles["BodyText"]))
        story.append(Spacer(1, 0.12 * cm))

    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("Sugestao para a proxima semana", styles["Heading2"]))
    story.append(
        Paragraph(
            "Escolha uma melhoria pequena: registrar pela tela Hoje, manter agua visivel ou fechar um bloco de foco por dia util.",
            styles["BodyText"],
        )
    )
    doc.build(story)


def _table(data: list[list[str]]) -> Table:
    table = Table(data, hAlign="LEFT", colWidths=[8 * cm, 7 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table
