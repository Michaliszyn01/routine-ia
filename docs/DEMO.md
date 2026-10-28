# Demonstração local da API

Executada em 28/10/2026, Python 3.12.14, Flask 3.0.3, com `create_app(enable_runtime=False)`, `TESTING=True` e banco temporário novo. Sem monitoramento, navegador, desktop, API de IA ou dados pessoais.

O cliente de teste HTTP criou uma tarefa de exemplo, concluiu a tarefa e consultou a central e o diagnóstico do SQLite. Resultado observado:

```json
{
  "database_integrity": "ok",
  "task_created_http": 201,
  "task_completed": "completed",
  "workspace_http": 200,
  "workspace_sections": [
    "current_focus",
    "daily",
    "date",
    "focus",
    "habits",
    "load_balance",
    "ok",
    "planner",
    "reviews",
    "studies",
    "tasks"
  ]
}
```

Isso verifica esse fluxo da API; não é screenshot nem validação do desktop/pywebview ou dos serviços de monitoramento. Para repetir, prepare requirements.txt e requirements-dev.txt e execute os testes focados:

```powershell
python -m pytest tests/test_workspace_refactor.py -q
```

Os testes configuram um diretório de dados temporário. A tarefa acima é fictícia e não representa um registro pessoal do proprietário.
