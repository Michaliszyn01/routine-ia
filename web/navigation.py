from __future__ import annotations


PRIMARY_NAV = (
    {"endpoint": "today_page", "label": "Hoje", "icon": "ri-circle-dot", "page": "today"},
    {"endpoint": "weekly_planner_page", "label": "Planejar", "icon": "ri-clipboard-list", "page": "weekly_planner"},
    {"endpoint": "studies_page", "label": "Estudos", "icon": "ri-book-open", "page": "studies"},
    {"endpoint": "focus_page", "label": "Foco", "icon": "ri-crosshair", "page": "focus"},
    {"endpoint": "evolution_page", "label": "Evolucao", "icon": "ri-trending-up", "page": "evolution"},
)


SECONDARY_NAV = (
    {"endpoint": "projects_page", "label": "Projetos", "icon": "ri-folder-open", "page": "projects"},
    {"endpoint": "habits_page", "label": "Habitos", "icon": "ri-sprout", "page": "habits"},
    {"endpoint": "life_goals_page", "label": "Objetivos", "icon": "ri-target", "page": "life_goals"},
    {"endpoint": "calendar_page", "label": "Calendario", "icon": "ri-calendar-days", "page": "calendar"},
)


APP_CATALOG = (
    {
        "label": "Rotina",
        "items": (
            {"endpoint": "today_page", "label": "Hoje", "icon": "ri-circle-dot"},
            {"endpoint": "daily_page", "label": "Registro diario", "icon": "ri-calendar-plus"},
            {"endpoint": "weekly_planner_page", "label": "Planejamento semanal", "icon": "ri-clipboard-list"},
            {"endpoint": "weekly_review_page", "label": "Revisao semanal", "icon": "ri-trending-up"},
            {"endpoint": "bad_day_page", "label": "Modo essencial", "icon": "ri-leaf"},
        ),
    },
    {
        "label": "Aprendizado",
        "items": (
            {"endpoint": "studies_page", "label": "Estudos", "icon": "ri-book-open"},
            {"endpoint": "focus_page", "label": "Foco", "icon": "ri-crosshair"},
            {"endpoint": "projects_page", "label": "Projetos", "icon": "ri-folder-open"},
            {"endpoint": "goals_page", "label": "Metas", "icon": "ri-medal"},
            {"endpoint": "life_goals_page", "label": "Objetivos", "icon": "ri-target"},
        ),
    },
    {
        "label": "Bem-estar",
        "items": (
            {"endpoint": "habits_page", "label": "Habitos", "icon": "ri-sprout"},
            {"endpoint": "health_page", "label": "Saude", "icon": "ri-monitor-check"},
            {"endpoint": "nutrition_page", "label": "Alimentacao", "icon": "ri-leaf"},
            {"endpoint": "calendar_page", "label": "Calendario", "icon": "ri-calendar-days"},
        ),
    },
    {
        "label": "Analise e sistema",
        "items": (
            {"endpoint": "evolution_page", "label": "Evolucao", "icon": "ri-trending-up"},
            {"endpoint": "analytics_page", "label": "Correlacoes", "icon": "ri-trending-up"},
            {"endpoint": "history_page", "label": "Historico", "icon": "ri-history"},
            {"endpoint": "app_usage_page", "label": "Uso do PC", "icon": "ri-monitor"},
            {"endpoint": "backup_page", "label": "Backup", "icon": "ri-file-text"},
            {"endpoint": "settings_page", "label": "Configuracoes", "icon": "ri-settings"},
        ),
    },
)
