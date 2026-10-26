# Update 3.5 - Base stabilization

Esta update estabiliza a base antes de avancar para planejamento inteligente.

## Entregas

- `routine_worker.py` para rodar tarefas continuas fora da interface.
- Controle de worker em `core/tools/background_worker/`.
- Monitoramento de PC comandado por estado persistido no SQLite:
  - `auto_start_monitoring`
  - `monitoring_worker_state`
  - `monitoring_interval_seconds`
- Health Importer coberto pelo worker em segundo plano.
- Status de worker exposto nas APIs e na tela Health Data.
- Health Data separada em modo simples e modo avancado.
- Dashboard com modo simples e avancado para reduzir excesso visual.

## Worker

O worker e iniciado automaticamente quando `background_worker_enabled=true`.

Em desenvolvimento:

```powershell
python routine_worker.py
```

No executavel:

```powershell
RoutineIA.exe --worker
```

O status fica em:

```txt
%LOCALAPPDATA%\RoutineIA\routine_worker_status.json
```

Logs:

```txt
%LOCALAPPDATA%\RoutineIA\logs\routine_worker.log
```

## Monitoramento continuo

As rotas existentes continuam iguais:

```txt
POST /api/monitoring-level1/start
POST /api/monitoring-level1/pause
POST /api/monitoring-level1/resume
POST /api/monitoring-level1/stop
GET  /api/monitoring-level1/status
```

A diferenca e que start/pause/resume/stop agora gravam o estado desejado no SQLite. O worker le esse estado e executa o monitoramento em segundo plano.

## Health Importer

O scheduler do Health Importer roda dentro do worker quando `health_auto_import_enabled=true`.

Ao iniciar o scheduler, ele faz uma tentativa inicial de importacao e depois segue o intervalo configurado.

A tela Health Data mostra:

- pasta configurada;
- status da pasta;
- ultima importacao;
- proxima importacao;
- importacao automatica;
- worker em segundo plano;
- cards de hoje;
- ultimos 7 dias.

Configuracoes, logs e registro manual ficam no modo avancado.

## Escopo preservado

Esta update nao adiciona IA coach, planejamento automatico, recomendacao medica, machine learning ou novas integracoes com Samsung/Google APIs.
