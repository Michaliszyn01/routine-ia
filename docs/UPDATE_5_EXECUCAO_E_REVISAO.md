# Update 5 - Execucao e Revisao

## Objetivo

A Update 5 transforma o Routine IA em um app que ajuda a executar blocos planejados e revisar a semana com dados locais. Ela adiciona:

- Modo Foco simples.
- Revisao Semanal forte.
- Integracao entre tela Hoje, sessoes de foco, monitoramento do PC, saude e blocos do plano.

Nao ha IA coach, bloqueio de apps, captura de tela, captura de teclado, Google Calendar, machine learning ou analise medica.

## Modo Foco

O Modo Foco cria sessoes vinculadas a um bloco do plano do dia ou sessoes avulsas de foco rapido.

Uma sessao registra:

- titulo;
- tipo de foco;
- bloco do plano, quando existir;
- tempo planejado;
- tempo real;
- tempo focado estimado;
- tempo fora do bloco;
- app atual em foco;
- eventos de iniciar, pausar, retomar, concluir e abandonar.

As tabelas usadas sao:

- `focus_sessions`;
- `focus_session_events`;
- `focus_app_usage`.

## Iniciar foco por um bloco

Na tela Hoje, blocos pendentes ou ativos exibem `Comecar foco`.

Ao iniciar:

1. O backend cria uma `focus_session`.
2. O bloco vira `active`.
3. A tela `/focus` abre a sessao.
4. O timer usa a duracao do bloco.

Ao concluir:

1. A sessao vira `completed`.
2. O bloco vinculado vira `done`.
3. O resumo da sessao mostra planejado, tempo real, foco estimado e tempo fora do bloco.

Ao abandonar:

1. A sessao vira `abandoned`.
2. O bloco pode continuar `pending` ou virar `skipped`.
3. O bloco nao e apagado automaticamente.

## Foco rapido

Na tela Modo Foco, o usuario pode iniciar uma sessao avulsa escolhendo:

- titulo;
- tipo;
- duracao.

Duracoes rapidas disponiveis:

- 10 minutos;
- 25 minutos;
- 50 minutos.

## Comparacao de apps esperados

As regras ficam em `core/tools/focus_mode/focus_rules.py`.

Tipos basicos:

- `study`;
- `project`;
- `workout`;
- `organization`;
- `reading`;
- `rest`;
- `generic`.

O app atual e comparado com os apps esperados do tipo de foco e recebe:

- `match`;
- `warning`;
- `mismatch`.

O sistema apenas registra e mostra alerta leve. Ele nao bloqueia apps.

## Tempo focado estimado

O Modo Foco reaproveita o monitoramento local da Update 1.1. Ele nao cria outro scanner.

Quando a tela consulta `/api/focus/current`, o backend observa o app em foco ja conhecido pelo monitoramento e soma:

- apps compativeis em `focused_seconds`;
- apps com aviso ou incompatibilidade em `distracted_seconds`.

Se nao houver monitoramento suficiente, a tela continua funcionando e apenas mostra menos dados.

## Revisao Semanal

A tela `/weekly-review` agrega:

- monitoramento do PC;
- dados de saude importados;
- plano do dia;
- sessoes de foco;
- blocos concluidos, pulados e reagendados;
- score de rotina;
- apps que mais tiraram foco.

Endpoints principais:

- `GET /api/weekly-review/current`;
- `GET /api/weekly-review/previous`;
- `GET /api/weekly-review/range?start=YYYY-MM-DD&end=YYYY-MM-DD`.

A resposta inclui:

- `summary`;
- `best_day`;
- `hard_day`;
- `focus_summary`;
- `health_summary`;
- `plan_summary`;
- `top_focus_breakers`;
- `insights`;
- `suggestions`.

## Dados ausentes

A revisao funciona mesmo sem dados de saude, foco, plano ou monitoramento. Nesses casos, mostra mensagem amigavel:

> Ainda ha poucos dados para uma revisao confiavel. Continue usando o app por mais alguns dias.

## Linguagem

A Update 5 usa linguagem construtiva:

- "Voce saiu um pouco do bloco."
- "Vamos pelo menor passo."
- "Ainda da para ajustar sem recomecar do zero."

Ela evita linguagem punitiva como "voce falhou", "voce foi improdutivo" ou "voce desperdicou a semana".

## Limitacoes

- Nao detecta abas do navegador.
- Nao captura tela.
- Nao captura teclado.
- Nao bloqueia aplicativos.
- Nao faz diagnostico medico.
- Nao cria planejamento semanal completo automaticamente.

## Fica para updates futuras

- IA coach.
- Bloqueador de apps.
- Notificacoes complexas.
- Google Calendar.
- Health Connect direto.
- App Android.
- Gamificacao avancada.
