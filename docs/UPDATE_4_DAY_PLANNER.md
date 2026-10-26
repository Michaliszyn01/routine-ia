# Update 4 - Day Planner

Esta update cria o primeiro planejador inteligente simples do dia.

## Objetivo

Responder com clareza:

```txt
O que eu faco agora?
```

O planejador usa energia atual, sono, treino, rotina diaria, produtividade recente, dados de saude e sinais simples da Update 3 para montar blocos realistas.

## Tela Hoje

A tela `/today` agora tem uma area de planejamento no topo:

- check-in rapido de energia;
- contexto rapido do dia;
- proximo passo claro;
- microtarefas simples do proximo bloco;
- blocos do dia;
- botao Gerar plano do dia;
- botao Reorganizar meu dia;
- acoes Comecar, Concluir e Pular.

## Check-in de energia

O check-in principal e:

- baixa;
- media;
- alta.

Tambem existem campos opcionais de foco e humor.

Energia baixa tende a gerar um dia leve. Energia media gera dia normal. Energia alta com sono bom permite dia forte.

## Modos

### Dia leve

Usado quando ha energia baixa, sono abaixo de 6 horas ou o dia precisa ser simplificado.

Caracteristicas:

- blocos menores;
- menos tarefas;
- mais pausas;
- minimo viavel.

### Dia normal

Usado como padrao para energia media.

Caracteristicas:

- blocos de 25 a 50 minutos;
- tarefas importantes;
- pausas normais.

### Dia forte

Usado quando energia esta alta e o sono esta bom.

Caracteristicas:

- tarefas dificeis primeiro;
- blocos maiores;
- foco em estudo e projeto.

## Reorganizar meu dia

O replanejamento:

- preserva blocos concluidos;
- ajusta o plano para ficar mais leve;
- cria novos blocos pendentes;
- usa linguagem construtiva.

Mensagem esperada:

```txt
Seu plano foi ajustado para ficar mais realista. Ainda da para salvar uma parte importante do dia.
```

## APIs

```txt
GET  /api/day-planner/today
POST /api/day-planner/generate
POST /api/day-planner/replan
POST /api/day-planner/checkin
POST /api/day-planner/block/start
POST /api/day-planner/block/complete
POST /api/day-planner/block/skip
```

## Tabelas

```txt
daily_plans
daily_plan_blocks
daily_energy_checkins
```

Status de blocos:

- pending;
- active;
- done;
- skipped;
- rescheduled.

## Limites atuais

- Nao usa IA coach.
- Nao integra Google Calendar.
- Nao cria notificacoes complexas.
- Nao faz planejamento semanal avancado.
- Nao bloqueia apps.
- Nao usa machine learning.
- Nao faz recomendacoes medicas.

## Fica para Update 5

- planejamento semanal mais inteligente;
- edicao manual refinada dos blocos;
- filtros por area;
- historico de planos;
- integracoes externas, se fizer sentido.

