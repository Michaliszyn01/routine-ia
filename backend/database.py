from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path

from .paths import (
    get_app_data_dir,
    get_backups_dir,
    get_database_path,
    get_exports_dir,
    resource_path,
)
from .db_engine import connect
from .migrations import run_migrations


APP_DATA_DIR = get_app_data_dir()
DATA_DIR = APP_DATA_DIR
EXPORTS_DIR = get_exports_dir()
BACKUPS_DIR = get_backups_dir()
DB_PATH = get_database_path()
LEGACY_DB_PATH = Path(resource_path("data/routine.db"))


DEFAULT_GOALS = [
    {
        "category": "workout",
        "label": "Treino",
        "weekly_days_goal": 5,
        "daily_hours_goal": 1,
        "weekly_hours_goal": 5,
        "daily_weight": 20,
        "max_daily_hours": 2,
        "active": 1,
    },
    {
        "category": "study",
        "label": "Estudo",
        "weekly_days_goal": 6,
        "daily_hours_goal": 2,
        "weekly_hours_goal": 12,
        "daily_weight": 25,
        "max_daily_hours": 4,
        "active": 1,
    },
    {
        "category": "programming",
        "label": "Programação",
        "weekly_days_goal": 5,
        "daily_hours_goal": 2,
        "weekly_hours_goal": 10,
        "daily_weight": 25,
        "max_daily_hours": 4,
        "active": 1,
    },
    {
        "category": "reading",
        "label": "Leitura",
        "weekly_days_goal": 4,
        "daily_hours_goal": 0.5,
        "weekly_hours_goal": 2,
        "daily_weight": 10,
        "max_daily_hours": 1,
        "active": 1,
    },
    {
        "category": "sleep",
        "label": "Sono",
        "weekly_days_goal": 7,
        "daily_hours_goal": 8,
        "weekly_hours_goal": 56,
        "daily_weight": 20,
        "max_daily_hours": 10,
        "active": 1,
    },
]

DEFAULT_SETTINGS = {
    "theme": "dark",
    "auto_open_browser": "true",
    "app_name": "Routine IA",
    "week_start": "monday",
    "desktop_mode": "true",
    "low_friction_mode": "false",
    "today_simplified_view": "false",
    "start_with_windows": "false",
    "start_minimized": "false",
    "run_in_background": "true",
    "background_worker_enabled": "true",
    "auto_start_monitoring": "false",
    "monitoring_worker_state": "off",
    "monitoring_interval_seconds": "60",
    "health_sync_base_path": r"G:\Meu Drive",
    "health_auto_import_enabled": "true",
    "health_import_interval_hours": "4",
    "ai_evaluation_enabled": "true",
    "ai_evaluation_model": "gemma3:4b",
    "ai_evaluation_url": "http://127.0.0.1:11434",
    "ai_evaluation_timeout_seconds": "8",
}

DEFAULT_STREAK_TYPES = [
    "daily_record",
    "workout",
    "study",
    "programming",
    "reading",
    "good_sleep",
    "good_score",
    "nutrition_good",
    "hydration_good",
    "focus_sessions",
]

DEFAULT_AUTO_BACKUP_SETTINGS = {
    "enabled": 1,
    "frequency": "daily",
    "keep_last": 10,
}

DEFAULT_APP_USAGE_SETTINGS = {
    "enabled": 0,
    "sample_interval_seconds": 2,
    "idle_timeout_seconds": 180,
    "store_window_titles": 1,
    "auto_start_with_app": 0,
    "pause_when_idle": 1,
}

DEFAULT_APP_USAGE_RULES = [
    {"process_name": "Code.exe", "app_name": "VS Code", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "code.exe", "app_name": "VS Code", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "Cursor.exe", "app_name": "Cursor", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "pycharm64.exe", "app_name": "PyCharm", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "WindowsTerminal.exe", "app_name": "Terminal", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "wt.exe", "app_name": "Terminal", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "cmd.exe", "app_name": "CMD", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "powershell.exe", "app_name": "PowerShell", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "pwsh.exe", "app_name": "PowerShell", "match_type": "process", "window_keyword": "", "category": "programacao", "productivity_level": "produtivo"},
    {"process_name": "EXCEL.EXE", "app_name": "Excel", "match_type": "process", "window_keyword": "", "category": "produtividade", "productivity_level": "produtivo"},
    {"process_name": "POWERPNT.EXE", "app_name": "PowerPoint", "match_type": "process", "window_keyword": "", "category": "produtividade", "productivity_level": "produtivo"},
    {"process_name": "WINWORD.EXE", "app_name": "Word", "match_type": "process", "window_keyword": "", "category": "produtividade", "productivity_level": "produtivo"},
    {"process_name": "chrome.exe", "app_name": "ChatGPT", "match_type": "process_and_keyword", "window_keyword": "ChatGPT", "category": "estudo", "productivity_level": "produtivo"},
    {"process_name": "chrome.exe", "app_name": "YouTube", "match_type": "process_and_keyword", "window_keyword": "YouTube", "category": "entretenimento", "productivity_level": "distracao"},
    {"process_name": "chrome.exe", "app_name": "Google Docs", "match_type": "process_and_keyword", "window_keyword": "Google Docs", "category": "estudo", "productivity_level": "produtivo"},
    {"process_name": "chrome.exe", "app_name": "Chrome", "match_type": "process", "window_keyword": "", "category": "navegador", "productivity_level": "neutro"},
    {"process_name": "msedge.exe", "app_name": "ChatGPT", "match_type": "process_and_keyword", "window_keyword": "ChatGPT", "category": "estudo", "productivity_level": "produtivo"},
    {"process_name": "msedge.exe", "app_name": "YouTube", "match_type": "process_and_keyword", "window_keyword": "YouTube", "category": "entretenimento", "productivity_level": "distracao"},
    {"process_name": "msedge.exe", "app_name": "Google Docs", "match_type": "process_and_keyword", "window_keyword": "Google Docs", "category": "estudo", "productivity_level": "produtivo"},
    {"process_name": "msedge.exe", "app_name": "Edge", "match_type": "process", "window_keyword": "", "category": "navegador", "productivity_level": "neutro"},
    {"process_name": "Discord.exe", "app_name": "Discord", "match_type": "process", "window_keyword": "", "category": "comunicacao", "productivity_level": "neutro"},
    {"process_name": "Spotify.exe", "app_name": "Spotify", "match_type": "process", "window_keyword": "", "category": "musica", "productivity_level": "neutro"},
    {"process_name": "steam.exe", "app_name": "Steam", "match_type": "process", "window_keyword": "", "category": "jogo", "productivity_level": "distracao"},
    {"process_name": "RobloxPlayerBeta.exe", "app_name": "Roblox", "match_type": "process", "window_keyword": "", "category": "jogo", "productivity_level": "distracao"},
    {"process_name": "EpicGamesLauncher.exe", "app_name": "Epic Games", "match_type": "process", "window_keyword": "", "category": "jogo", "productivity_level": "distracao"},
]

DEFAULT_CHECKLISTS = [
    {
        "name": "Antes de estudar",
        "category": "estudo",
        "description": "Preparar um bloco curto de estudo sem atrito.",
        "items": ["Abrir material", "Tirar distracoes", "Iniciar timer", "Fazer primeira questao"],
    },
    {
        "name": "Antes de programar",
        "category": "programacao",
        "description": "Entrar no contexto de codigo com uma tarefa pequena.",
        "items": ["Abrir VS Code", "Abrir projeto", "Escolher tarefa pequena", "Rodar app ou teste"],
    },
    {
        "name": "Antes de dormir",
        "category": "sono",
        "description": "Fechar o dia e reduzir friccao para amanha.",
        "items": ["Salvar dia", "Ver amanha", "Desligar distracoes", "Preparar sono"],
    },
    {
        "name": "Dia ruim",
        "category": "bad_day",
        "description": "Manter continuidade em um dia dificil.",
        "items": ["Agua", "Minimo util", "Alimentacao", "Descanso"],
    },
    {
        "name": "Antes de sair de casa",
        "category": "saida",
        "description": "Checklist rapido para evitar esquecimento.",
        "items": ["Celular", "Carteira", "Chave", "Garrafa", "Compromisso"],
    },
]

DEFAULT_ACTIVATION_CHAINS = [
    {
        "name": "Estudar matematica",
        "category": "estudo",
        "description": "Quebrar estudo em passos pequenos.",
        "steps": ["Abrir material", "Escolher 5 questoes", "Fazer a primeira questao", "Corrigir uma questao", "Marcar dificuldade"],
    },
    {
        "name": "Programar Routine IA",
        "category": "programacao",
        "description": "Entrar no codigo sem travar.",
        "steps": ["Abrir VS Code", "Abrir o projeto", "Escolher uma tarefa pequena", "Alterar um arquivo", "Rodar app ou teste"],
    },
    {
        "name": "Organizar rotina",
        "category": "rotina",
        "description": "Salvar o dia com o minimo de decisao.",
        "steps": ["Abrir tela Hoje", "Salvar energia e humor", "Ver proxima acao", "Escolher um bloco de 5 minutos", "Salvar minimo"],
    },
]


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    migrate_legacy_database()


def migrate_legacy_database() -> None:
    if DB_PATH.exists() or not LEGACY_DB_PATH.exists():
        return

    try:
        if LEGACY_DB_PATH.resolve() == DB_PATH.resolve():
            return
    except OSError:
        pass

    try:
        shutil.copy2(LEGACY_DB_PATH, DB_PATH)
    except OSError:
        return


def get_connection() -> sqlite3.Connection:
    ensure_data_dirs()
    return connect(DB_PATH)


def init_db() -> None:
    ensure_data_dirs()
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                weekday TEXT NOT NULL,
                workout_done INTEGER NOT NULL DEFAULT 0,
                workout_hours REAL NOT NULL DEFAULT 0,
                study_done INTEGER NOT NULL DEFAULT 0,
                study_hours REAL NOT NULL DEFAULT 0,
                programming_done INTEGER NOT NULL DEFAULT 0,
                programming_hours REAL NOT NULL DEFAULT 0,
                game_hours REAL NOT NULL DEFAULT 0,
                reading_done INTEGER NOT NULL DEFAULT 0,
                reading_hours REAL NOT NULL DEFAULT 0,
                sleep_hours REAL NOT NULL DEFAULT 0,
                steps INTEGER NOT NULL DEFAULT 0,
                energy INTEGER NOT NULL DEFAULT 3,
                mood INTEGER NOT NULL DEFAULT 3,
                daily_score REAL NOT NULL DEFAULT 0,
                observation TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL DEFAULT '',
                weekly_days_goal INTEGER NOT NULL DEFAULT 0,
                daily_hours_goal REAL NOT NULL DEFAULT 0,
                weekly_hours_goal REAL NOT NULL DEFAULT 0,
                daily_weight REAL NOT NULL DEFAULT 0,
                max_daily_hours REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS health_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sleep_hours_auto REAL NOT NULL DEFAULT 0,
                steps_auto INTEGER NOT NULL DEFAULT 0,
                workout_minutes_auto INTEGER NOT NULL DEFAULT 0,
                average_heart_rate INTEGER NOT NULL DEFAULT 0,
                resting_heart_rate INTEGER NOT NULL DEFAULT 0,
                stress_average REAL NOT NULL DEFAULT 0,
                weight_kg REAL NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'Manual',
                observation TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, source)
            );

            CREATE TABLE IF NOT EXISTS health_imported_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                data_type TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                rows_imported INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT NOT NULL DEFAULT '',
                UNIQUE(file_hash, data_type)
            );

            CREATE TABLE IF NOT EXISTS health_import_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_key TEXT NOT NULL UNIQUE,
                data_type TEXT NOT NULL,
                date TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source_file TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS health_sleep_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_sleep_seconds INTEGER NOT NULL DEFAULT 0,
                light_sleep_seconds INTEGER NOT NULL DEFAULT 0,
                deep_sleep_seconds INTEGER NOT NULL DEFAULT 0,
                rem_sleep_seconds INTEGER NOT NULL DEFAULT 0,
                awake_seconds INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS health_steps_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_steps INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS health_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL DEFAULT '',
                activity_type TEXT NOT NULL DEFAULT '',
                activity_name TEXT NOT NULL DEFAULT '',
                elapsed_seconds INTEGER NOT NULL DEFAULT 0,
                active_seconds INTEGER NOT NULL DEFAULT 0,
                distance_km REAL NOT NULL DEFAULT 0,
                source_file TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, start_time, activity_type, elapsed_seconds, distance_km)
            );

            CREATE TABLE IF NOT EXISTS health_heart_rate_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                avg_bpm INTEGER NOT NULL DEFAULT 0,
                min_bpm INTEGER NOT NULL DEFAULT 0,
                max_bpm INTEGER NOT NULL DEFAULT 0,
                samples_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_health_import_records_date ON health_import_records(date);
            CREATE INDEX IF NOT EXISTS idx_health_activities_date ON health_activities(date);

            CREATE TABLE IF NOT EXISTS weekly_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                average_score REAL NOT NULL DEFAULT 0,
                total_workout_hours REAL NOT NULL DEFAULT 0,
                total_study_hours REAL NOT NULL DEFAULT 0,
                total_programming_hours REAL NOT NULL DEFAULT 0,
                total_reading_hours REAL NOT NULL DEFAULT 0,
                average_sleep REAL NOT NULL DEFAULT 0,
                total_steps INTEGER NOT NULL DEFAULT 0,
                average_energy REAL NOT NULL DEFAULT 0,
                average_mood REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_start, week_end)
            );

            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS weekly_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_start, week_end)
            );

            CREATE TABLE IF NOT EXISTS backups_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'success',
                message TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS streaks_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                streak_type TEXT NOT NULL UNIQUE,
                current_count INTEGER NOT NULL DEFAULT 0,
                best_count INTEGER NOT NULL DEFAULT 0,
                last_valid_date TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Outro',
                status TEXT NOT NULL DEFAULT 'ativo',
                color TEXT NOT NULL DEFAULT '#22d3ee',
                weekly_hours_goal REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS project_time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                minutes INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'manual',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                project_id INTEGER,
                category TEXT NOT NULL DEFAULT 'outro',
                duration_minutes INTEGER NOT NULL DEFAULT 25,
                break_minutes INTEGER NOT NULL DEFAULT 5,
                completed INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS nutrition_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                breakfast_done INTEGER NOT NULL DEFAULT 0,
                lunch_done INTEGER NOT NULL DEFAULT 0,
                dinner_done INTEGER NOT NULL DEFAULT 0,
                healthy_snack_done INTEGER NOT NULL DEFAULT 0,
                water_liters REAL NOT NULL DEFAULT 0,
                protein_ok INTEGER NOT NULL DEFAULT 0,
                fruits_vegetables_ok INTEGER NOT NULL DEFAULT 0,
                ultra_processed_control INTEGER NOT NULL DEFAULT 0,
                meals_count INTEGER NOT NULL DEFAULT 0,
                nutrition_score REAL NOT NULL DEFAULT 0,
                observation TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                report_text TEXT NOT NULL DEFAULT '',
                score_average REAL NOT NULL DEFAULT 0,
                nutrition_average REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_start, week_end)
            );


            CREATE TABLE IF NOT EXISTS life_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Outro',
                priority TEXT NOT NULL DEFAULT 'media',
                status TEXT NOT NULL DEFAULT 'ativo',
                target_date TEXT,
                linked_area TEXT NOT NULL DEFAULT '',
                progress_percent REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS weekly_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL UNIQUE,
                week_end TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                generated_by TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS weekly_plan_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                weekday TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                estimated_minutes INTEGER NOT NULL DEFAULT 0,
                linked_project_id INTEGER,
                linked_goal_id INTEGER,
                completed INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(plan_id) REFERENCES weekly_plans(id) ON DELETE CASCADE,
                FOREIGN KEY(linked_project_id) REFERENCES projects(id) ON DELETE SET NULL,
                FOREIGN KEY(linked_goal_id) REFERENCES life_goals(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS daily_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                mode TEXT NOT NULL DEFAULT 'normal',
                suggested_mode TEXT NOT NULL DEFAULT 'normal',
                energy_level TEXT NOT NULL DEFAULT 'media',
                sleep_seconds INTEGER NOT NULL DEFAULT 0,
                routine_score REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_plan_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT 'task',
                start_time TEXT NOT NULL DEFAULT '',
                duration_minutes INTEGER NOT NULL DEFAULT 25,
                priority INTEGER NOT NULL DEFAULT 3,
                status TEXT NOT NULL DEFAULT 'pending',
                linked_task_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(plan_id) REFERENCES daily_plans(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS daily_energy_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                energy_level TEXT NOT NULL DEFAULT 'media',
                focus_level TEXT NOT NULL DEFAULT '',
                mood_level TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS weekly_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                what_worked TEXT NOT NULL DEFAULT '',
                what_failed TEXT NOT NULL DEFAULT '',
                best_day TEXT NOT NULL DEFAULT '',
                worst_day TEXT NOT NULL DEFAULT '',
                main_obstacle TEXT NOT NULL DEFAULT '',
                main_win TEXT NOT NULL DEFAULT '',
                next_week_adjustment TEXT NOT NULL DEFAULT '',
                emotional_state TEXT NOT NULL DEFAULT '',
                energy_reflection TEXT NOT NULL DEFAULT '',
                discipline_score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_start, week_end)
            );

            CREATE TABLE IF NOT EXISTS smart_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                severity TEXT NOT NULL DEFAULT 'info',
                related_date TEXT,
                dismissed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS custom_habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Outro',
                frequency TEXT NOT NULL DEFAULT 'diaria',
                target_per_week INTEGER NOT NULL DEFAULT 5,
                weight INTEGER NOT NULL DEFAULT 5,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                value TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(habit_id, date),
                FOREIGN KEY(habit_id) REFERENCES custom_habits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT 'Outro',
                topic TEXT NOT NULL DEFAULT '',
                duration_minutes INTEGER NOT NULL DEFAULT 0,
                questions_done INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                wrong_answers INTEGER NOT NULL DEFAULT 0,
                difficulty INTEGER NOT NULL DEFAULT 3,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mock_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                exam_name TEXT NOT NULL DEFAULT '',
                area TEXT NOT NULL DEFAULT '',
                score REAL NOT NULL DEFAULT 0,
                total_questions INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                wrong_answers INTEGER NOT NULL DEFAULT 0,
                essay_score REAL NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS study_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT 'Outro',
                topic TEXT NOT NULL DEFAULT '',
                error_type TEXT NOT NULL DEFAULT 'conteudo',
                description TEXT NOT NULL DEFAULT '',
                correction TEXT NOT NULL DEFAULT '',
                reviewed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bad_day_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                preset TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                minimum_actions_done TEXT NOT NULL DEFAULT '[]',
                note TEXT NOT NULL DEFAULT '',
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS minimum_day_saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                energy INTEGER NOT NULL DEFAULT 3,
                mood INTEGER NOT NULL DEFAULT 3,
                sleep_hours REAL NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS microtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                estimated_minutes INTEGER NOT NULL DEFAULT 2,
                completed INTEGER NOT NULL DEFAULT 0,
                order_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS activation_chain_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'rotina',
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS activation_chain_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                estimated_minutes INTEGER NOT NULL DEFAULT 2,
                order_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(template_id) REFERENCES activation_chain_templates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS checklist_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'rotina',
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                order_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(template_id) REFERENCES checklist_templates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS checklist_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                completed_items_json TEXT NOT NULL DEFAULT '[]',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(template_id) REFERENCES checklist_templates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS adhd_cant_start_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                energy_level TEXT NOT NULL DEFAULT '',
                desired_area TEXT NOT NULL DEFAULT '',
                available_minutes INTEGER NOT NULL DEFAULT 5,
                suggested_action TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS command_center_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                action_title TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT '',
                source_id TEXT,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_life_goals_status ON life_goals(status);
            CREATE INDEX IF NOT EXISTS idx_weekly_plan_items_date ON weekly_plan_items(date);
            CREATE INDEX IF NOT EXISTS idx_daily_plan_blocks_plan ON daily_plan_blocks(plan_id);
            CREATE INDEX IF NOT EXISTS idx_daily_energy_checkins_date ON daily_energy_checkins(date);
            CREATE INDEX IF NOT EXISTS idx_habit_logs_date ON habit_logs(date);
            CREATE INDEX IF NOT EXISTS idx_study_sessions_date ON study_sessions(date);
            CREATE INDEX IF NOT EXISTS idx_study_errors_reviewed ON study_errors(reviewed);
            CREATE INDEX IF NOT EXISTS idx_microtasks_date ON microtasks(date);
            CREATE INDEX IF NOT EXISTS idx_checklist_logs_date ON checklist_logs(date);
            CREATE INDEX IF NOT EXISTS idx_minimum_day_saves_date ON minimum_day_saves(date);


            CREATE TABLE IF NOT EXISTS app_usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                process_name TEXT NOT NULL,
                app_name TEXT NOT NULL DEFAULT '',
                window_title TEXT NOT NULL DEFAULT '',
                executable_path TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'outro',
                productivity_level TEXT NOT NULL DEFAULT 'neutro',
                linked_project_id INTEGER,
                is_active_session INTEGER NOT NULL DEFAULT 0,
                last_heartbeat_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(linked_project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS app_usage_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_name TEXT NOT NULL DEFAULT '',
                app_name TEXT NOT NULL DEFAULT '',
                match_type TEXT NOT NULL DEFAULT 'process',
                window_keyword TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'outro',
                productivity_level TEXT NOT NULL DEFAULT 'neutro',
                linked_project_id INTEGER,
                auto_add_to_project_time INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(linked_project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS app_usage_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 0,
                sample_interval_seconds INTEGER NOT NULL DEFAULT 2,
                idle_timeout_seconds INTEGER NOT NULL DEFAULT 180,
                store_window_titles INTEGER NOT NULL DEFAULT 1,
                auto_start_with_app INTEGER NOT NULL DEFAULT 0,
                pause_when_idle INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_app_usage_events_date ON app_usage_events(date);
            CREATE INDEX IF NOT EXISTS idx_app_usage_events_process ON app_usage_events(process_name);
            CREATE INDEX IF NOT EXISTS idx_app_usage_events_active ON app_usage_events(is_active_session);
            CREATE INDEX IF NOT EXISTS idx_app_usage_rules_process ON app_usage_rules(process_name);

            CREATE TABLE IF NOT EXISTS monitoring_app_usage_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                app_name TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT 'Neutro',
                total_seconds INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, app_name)
            );

            CREATE INDEX IF NOT EXISTS idx_monitoring_app_usage_daily_date
                ON monitoring_app_usage_daily(date);
            CREATE INDEX IF NOT EXISTS idx_monitoring_app_usage_daily_label
                ON monitoring_app_usage_daily(label);

            CREATE TABLE IF NOT EXISTS auto_backup_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 1,
                frequency TEXT NOT NULL DEFAULT 'daily',
                keep_last INTEGER NOT NULL DEFAULT 10,
                last_backup_at TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        _migrate_schema(conn)
        run_migrations(conn)
        _seed_goals(conn)
        _seed_settings(conn)
        _seed_streaks(conn)
        _seed_auto_backup_settings(conn)
        _seed_app_usage_settings(conn)
        _seed_app_usage_rules(conn)
        _seed_checklist_templates(conn)
        _seed_activation_chain_templates(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "goals", "label", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "daily_records", "game_hours", "REAL NOT NULL DEFAULT 0")
    _ensure_column(conn, "app_usage_events", "app_name", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "app_usage_events", "window_title", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "app_usage_events", "executable_path", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "app_usage_events", "linked_project_id", "INTEGER")
    _ensure_column(conn, "app_usage_events", "is_active_session", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "app_usage_events", "last_heartbeat_at", "TEXT")
    _ensure_column(conn, "app_usage_rules", "app_name", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "app_usage_rules", "match_type", "TEXT NOT NULL DEFAULT 'process'")
    _ensure_column(conn, "app_usage_rules", "window_keyword", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "app_usage_rules", "linked_project_id", "INTEGER")
    _ensure_column(conn, "app_usage_rules", "auto_add_to_project_time", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "app_usage_settings", "sample_interval_seconds", "INTEGER NOT NULL DEFAULT 2")
    _ensure_column(conn, "app_usage_settings", "idle_timeout_seconds", "INTEGER NOT NULL DEFAULT 180")
    _ensure_column(conn, "app_usage_settings", "store_window_titles", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "app_usage_settings", "auto_start_with_app", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "app_usage_settings", "pause_when_idle", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "bad_day_logs", "preset", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "bad_day_logs", "completed_at", "TEXT")
    _ensure_column(conn, "bad_day_logs", "updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")

    for goal in DEFAULT_GOALS:
        conn.execute(
            "UPDATE goals SET label = ? WHERE category = ? AND (label IS NULL OR label = '')",
            (goal["label"], goal["category"]),
        )


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    existing_columns = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing_columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_goals(conn: sqlite3.Connection) -> None:
    for goal in DEFAULT_GOALS:
        conn.execute(
            """
            INSERT OR IGNORE INTO goals (
                category,
                label,
                weekly_days_goal,
                daily_hours_goal,
                weekly_hours_goal,
                daily_weight,
                max_daily_hours,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                goal["category"],
                goal["label"],
                goal["weekly_days_goal"],
                goal["daily_hours_goal"],
                goal["weekly_hours_goal"],
                goal["daily_weight"],
                goal["max_daily_hours"],
                goal["active"],
            ),
        )


def _seed_settings(conn: sqlite3.Connection) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )


def _seed_streaks(conn: sqlite3.Connection) -> None:
    for streak_type in DEFAULT_STREAK_TYPES:
        conn.execute(
            "INSERT OR IGNORE INTO streaks_cache (streak_type) VALUES (?)",
            (streak_type,),
        )


def _seed_auto_backup_settings(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO auto_backup_settings (id, enabled, frequency, keep_last)
        VALUES (1, ?, ?, ?)
        """,
        (
            DEFAULT_AUTO_BACKUP_SETTINGS["enabled"],
            DEFAULT_AUTO_BACKUP_SETTINGS["frequency"],
            DEFAULT_AUTO_BACKUP_SETTINGS["keep_last"],
        ),
    )

def _seed_app_usage_settings(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO app_usage_settings (
            id, enabled, sample_interval_seconds, idle_timeout_seconds,
            store_window_titles, auto_start_with_app, pause_when_idle
        )
        VALUES (1, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_APP_USAGE_SETTINGS["enabled"],
            DEFAULT_APP_USAGE_SETTINGS["sample_interval_seconds"],
            DEFAULT_APP_USAGE_SETTINGS["idle_timeout_seconds"],
            DEFAULT_APP_USAGE_SETTINGS["store_window_titles"],
            DEFAULT_APP_USAGE_SETTINGS["auto_start_with_app"],
            DEFAULT_APP_USAGE_SETTINGS["pause_when_idle"],
        ),
    )
    conn.execute(
        """
        UPDATE app_usage_settings
        SET sample_interval_seconds = 2
        WHERE id = 1 AND sample_interval_seconds = 5
        """
    )


def _seed_app_usage_rules(conn: sqlite3.Connection) -> None:
    for rule in DEFAULT_APP_USAGE_RULES:
        existing = conn.execute(
            """
            SELECT id FROM app_usage_rules
            WHERE lower(process_name) = lower(?) AND match_type = ? AND lower(window_keyword) = lower(?)
            """,
            (rule["process_name"], rule["match_type"], rule["window_keyword"]),
        ).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO app_usage_rules (
                process_name, app_name, match_type, window_keyword,
                category, productivity_level, active
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                rule["process_name"],
                rule["app_name"],
                rule["match_type"],
                rule["window_keyword"],
                rule["category"],
                rule["productivity_level"],
            ),
        )


def _seed_checklist_templates(conn: sqlite3.Connection) -> None:
    for template in DEFAULT_CHECKLISTS:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO checklist_templates (name, category, description, active)
            VALUES (?, ?, ?, 1)
            """,
            (template["name"], template["category"], template["description"]),
        )
        row = conn.execute(
            "SELECT id FROM checklist_templates WHERE name = ?",
            (template["name"],),
        ).fetchone()
        if not row:
            continue
        template_id = int(row["id"])
        existing_items = conn.execute(
            "SELECT COUNT(*) AS total FROM checklist_items WHERE template_id = ?",
            (template_id,),
        ).fetchone()["total"]
        if int(existing_items or 0):
            continue
        for index, title in enumerate(template["items"]):
            conn.execute(
                """
                INSERT INTO checklist_items (template_id, title, order_index)
                VALUES (?, ?, ?)
                """,
                (template_id, title, index),
            )


def _seed_activation_chain_templates(conn: sqlite3.Connection) -> None:
    for template in DEFAULT_ACTIVATION_CHAINS:
        conn.execute(
            """
            INSERT OR IGNORE INTO activation_chain_templates (name, category, description, active)
            VALUES (?, ?, ?, 1)
            """,
            (template["name"], template["category"], template["description"]),
        )
        row = conn.execute(
            "SELECT id FROM activation_chain_templates WHERE name = ?",
            (template["name"],),
        ).fetchone()
        if not row:
            continue
        template_id = int(row["id"])
        existing_steps = conn.execute(
            "SELECT COUNT(*) AS total FROM activation_chain_steps WHERE template_id = ?",
            (template_id,),
        ).fetchone()["total"]
        if int(existing_steps or 0):
            continue
        for index, title in enumerate(template["steps"][:5]):
            conn.execute(
                """
                INSERT INTO activation_chain_steps (template_id, title, estimated_minutes, order_index)
                VALUES (?, ?, ?, ?)
                """,
                (template_id, title, 1 if index == 0 else 2, index),
            )
