from __future__ import annotations

from functools import partial

from flask import Flask, render_template

from .navigation import APP_CATALOG, PRIMARY_NAV, SECONDARY_NAV


PAGE_ROUTES = (
    ("/", "today_home_page", "workspace.html", "today", "Hoje"),
    ("/today", "today_page", "workspace.html", "today", "Hoje"),
    ("/daily", "daily_page", "daily.html", "daily", "Registro diario"),
    ("/goals", "goals_page", "goals.html", "goals", "Metas"),
    ("/history", "history_page", "history.html", "history", "Historico"),
    ("/calendar", "calendar_page", "calendar.html", "calendar", "Calendario"),
    ("/nutrition", "nutrition_page", "nutrition.html", "nutrition", "Alimentacao"),
    ("/health", "health_page", "health.html", "health", "Saude"),
    ("/focus", "focus_page", "focus.html", "focus", "Foco"),
    ("/projects", "projects_page", "projects.html", "projects", "Projetos"),
    ("/backup", "backup_page", "backup.html", "backup", "Backup"),
    ("/settings", "settings_page", "settings.html", "settings", "Configuracoes"),
    ("/goals-life", "life_goals_page", "life_goals.html", "life_goals", "Objetivos"),
    ("/weekly-planner", "weekly_planner_page", "weekly_planner.html", "weekly_planner", "Planejamento"),
    ("/weekly-review", "weekly_review_page", "weekly_review.html", "weekly_review", "Revisao semanal"),
    ("/habits", "habits_page", "habits.html", "habits", "Habitos"),
    ("/studies", "studies_page", "studies.html", "studies", "Estudos"),
    ("/bad-day", "bad_day_page", "bad_day.html", "bad_day", "Modo essencial"),
    ("/evolution", "evolution_page", "evolution.html", "evolution", "Evolucao"),
    ("/analytics", "analytics_page", "analytics.html", "analytics", "Correlacoes"),
    ("/app-usage", "app_usage_page", "app_usage_level1.html", "app_usage", "Uso do PC"),
)


def register_page_routes(app: Flask) -> None:
    for rule, endpoint, template, active_page, title in PAGE_ROUTES:
        view = partial(_render_page, template, active_page, title)
        app.add_url_rule(rule, endpoint=endpoint, view_func=view, methods=["GET"])

    @app.get("/favicon.ico")
    def favicon():
        return app.send_static_file("img/app-icon.svg")

    @app.context_processor
    def inject_navigation():
        return {
            "primary_navigation": PRIMARY_NAV,
            "secondary_navigation": SECONDARY_NAV,
            "app_catalog": APP_CATALOG,
        }


def _render_page(template: str, active_page: str, title: str):
    return render_template(template, active_page=active_page, page_title=title)
