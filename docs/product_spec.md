# Routine IA - Product Spec

## Objetivo

Substituir uma planilha de rotina diaria por um aplicativo local, simples e evolutivo, capaz de registrar habitos, saude, produtividade e historico pessoal.

## Produto atual

O produto atual preserva o MVP original e adiciona a camada Life OS v2+:

1. Dashboard semanal
2. Tela Hoje rapida
3. Registro diario completo
4. Metas e metas inteligentes
5. Historico
6. Calendario mensal
7. Alimentacao/nutricao
8. Health Data manual
9. Timer de foco
10. Projetos
11. Backup e exportacao
12. Relatorio semanal em JSON e PDF
13. Configuracoes locais

## Modulos v2

- `backend/streaks.py`: sequencias de rotina, treino, estudo, programacao, leitura, sono, score, alimentacao, hidratacao e foco.
- `backend/insights.py`: comparacao entre semana atual e semana anterior.
- `backend/calendar_utils.py`: calendario mensal com resumo por dia.
- `backend/smart_goals.py`: sugestoes de ajuste de metas sem alterar dados automaticamente.
- `backend/nutrition.py`: registro alimentar saudavel, pontuacao por consistencia e hidratacao.
- `backend/focus_timer.py`: sessoes de foco, conclusao e espelhamento opcional no registro diario.
- `backend/projects.py`: projetos, metas semanais e tempo manual ou vindo do foco.
- `backend/pdf_report.py`: PDF semanal em `AppData\Local\RoutineIA\exports\reports`.
- `backend/backup.py`: backup manual e automatico com retencao.

## Modulos v3/v4

1. Objetivos de vida
2. Planejamento semanal
3. Revisao semanal
4. Habitos personalizados
5. Estudos/simulados/erros
6. Alertas e padroes
7. Dia Ruim
8. Evolucao pessoal
9. Uso local do PC, desligado por padrao

## Banco de dados

O SQLite e criado automaticamente pelo modulo `backend/database.py` em uma pasta persistente do usuario.

No Windows, o caminho padrao e:

```text
C:\Users\SEU_USUARIO\AppData\Local\RoutineIA\routine.db
```

Em desenvolvimento ou testes, o caminho pode ser sobrescrito com `ROUTINE_IA_DATA_DIR`.

Tabelas principais:

- `daily_records`
- `goals`
- `health_data`
- `settings`
- `weekly_summary`
- `weekly_notes`
- `backups_log`
- `streaks_cache`
- `projects`
- `project_time_entries`
- `focus_sessions`
- `nutrition_records`
- `weekly_reports`
- `auto_backup_settings`

## Regras centrais

- O backend e a fonte de verdade para pontuacao.
- O frontend apenas coleta dados e exibe resultados.
- A data e unica em `daily_records`, entao salvar uma data existente atualiza o registro.
- Metas sao configuraveis na tela de metas.
- A soma ideal dos pesos ativos e 100.
- Configuracoes locais controlam tema, nome do app e abertura automatica do navegador no modo web.
- Historico, Health Data, alimentacao, foco, projetos e tempo por projeto podem exportar CSV para `AppData\Local\RoutineIA\exports`.
- Health Data pode importar CSV simples.
- Backups manuais e automaticos copiam o SQLite inteiro para `AppData\Local\RoutineIA\backups`.

## Modos de execucao

- `python app.py`: modo web de desenvolvimento. Inicia Flask em `127.0.0.1:5000` e abre o navegador padrao, salvo quando `ROUTINE_IA_OPEN_BROWSER=0`.
- `python desktop.py`: modo desktop. Inicia Flask em uma thread e abre uma janela propria com pywebview.
- `dist\RoutineIA.exe`: modo desktop empacotado. Usa `desktop.py` como entrada principal, sem terminal e sem navegador externo.

## Rotas principais

HTML:

- `/`
- `/today`
- `/daily`
- `/goals`
- `/history`
- `/calendar`
- `/nutrition`
- `/health`
- `/focus`
- `/projects`
- `/backup`
- `/settings`

API:

- `/api/dashboard`
- `/api/today`
- `/api/daily`
- `/api/streaks`
- `/api/week-comparison`
- `/api/calendar`
- `/api/smart-goals`
- `/api/goals`
- `/api/goals/reset`
- `/api/history`
- `/api/history/export`
- `/api/health`
- `/api/health/export`
- `/api/health/import`
- `/api/nutrition`
- `/api/nutrition/history`
- `/api/nutrition/export`
- `/api/focus/sessions`
- `/api/focus/start`
- `/api/focus/complete`
- `/api/focus/save`
- `/api/focus/export`
- `/api/projects`
- `/api/projects/export`
- `/api/projects/time/export`
- `/api/reports/weekly`
- `/api/reports/weekly/pdf`
- `/api/settings`
- `/api/settings/reset`
- `/api/backup/create`
- `/api/backup/list`
- `/api/backup/settings`
- `/api/app/paths`

## Empacotamento Windows

- `backend/paths.py` resolve caminhos de templates e arquivos estaticos em desenvolvimento e no PyInstaller.
- `RoutineIA.spec` usa `desktop.py` como entrada principal do executavel.
- `RoutineIA.spec` inclui a pasta `frontend` inteira no executavel, preservando templates, CSS, JS, Chart.js, icone e assets.
- O executavel usa o icone `frontend/static/assets/icon.ico`.
- O executavel e gerado com `console=False`.
- `desktop.py` roda Flask com `debug=False` e `use_reloader=False`.
- O banco nao e salvo dentro de `sys._MEIPASS` nem dentro da pasta temporaria do executavel.

## Futuro

Arquitetura reservada para:

- Relatorio semanal com IA
- Importacao Samsung Health por CSV
- Integracao Health Connect
- Sistema de conquistas
- Sincronizacao opcional, se um dia fizer sentido, mantendo modo local como padrao
