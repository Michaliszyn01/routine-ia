# Monitoramento Nivel 1

## O que faz

O monitoramento nivel 1 registra, localmente, quanto tempo aplicativos relevantes ficam abertos no computador.

O ciclo padrao e simples:

1. listar processos abertos com `psutil`;
2. ignorar processos internos do sistema;
3. normalizar o nome do aplicativo;
4. aplicar uma regra manual de rotulo;
5. somar o intervalo configurado para cada app aberto;
6. salvar o total diario no SQLite local.

O intervalo padrao e de 60 segundos. A estrutura aceita trocar para 30 segundos ou 120 segundos sem alterar o modelo de banco.

## O que nao faz

Este nivel nao captura tela, nao grava teclado, nao le abas do navegador, nao analisa conteudo visual, nao bloqueia aplicativos e nao tenta medir foco perfeito.

Ele mede aplicativo aberto, nao aplicativo em foco.

## Estrutura

O codigo fica em:

```txt
core/
  tools/
    monitoring/
      process_scanner.py
      usage_tracker.py
      app_rules.py
      monitoring_repository.py
      monitoring_service.py
```

Responsabilidades:

- `process_scanner.py`: lista processos e remove processos irrelevantes.
- `usage_tracker.py`: calcula incrementos de tempo por app aberto.
- `app_rules.py`: concentra regras manuais e pontuacao por rotulo.
- `monitoring_repository.py`: salva e consulta o SQLite.
- `monitoring_service.py`: orquestra thread, scanner, tracker e resumo.

## Banco

Tabela criada:

```txt
monitoring_app_usage_daily
```

Campos principais:

- `date`
- `app_name`
- `label`
- `total_seconds`
- `created_at`
- `updated_at`

A chave unica e `date + app_name`, entao novas leituras atualizam o mesmo registro diario em vez de duplicar linhas.

## Rotulos

Rotulos iniciais:

- `Produtivo`
- `Estudo`
- `Projeto`
- `Neutro`
- `Comunicacao`
- `Lazer`
- `Distracao`
- `Risco`

Regras iniciais ficam em `core/tools/monitoring/app_rules.py`.

Exemplos:

- `Code.exe` -> `VS Code`, `Projeto`
- `Anki.exe` -> `Anki`, `Estudo`
- `Chrome.exe` -> `Chrome`, `Neutro`
- `Spotify.exe` -> `Spotify`, `Neutro`
- `Discord.exe` -> `Discord`, `Risco`
- `steam.exe` -> `Steam`, `Lazer`

Para alterar uma regra, edite `DEFAULT_RULES` em `app_rules.py`.

## Pontuacao

A pontuacao e propositalmente simples:

- `Projeto`, `Produtivo`, `Estudo`: positivo
- `Neutro`, `Comunicacao`: neutro
- `Lazer`: levemente negativo
- `Risco`, `Distracao`: negativo

Os pesos ficam em `LABEL_SCORE`, tambem em `app_rules.py`.

## Limitacoes

- Se um processo fica aberto em segundo plano, ele pode somar tempo mesmo sem uso real.
- Chrome e outros navegadores ficam neutros no nivel 1, porque abas nao sao lidas.
- O monitor nao sabe se o usuario estava realmente olhando para o app.
- Varios processos do mesmo app sao agrupados para evitar contagem duplicada desnecessaria.

## Evolucao futura

Possiveis evolucoes, sem fazer parte desta update:

- tela de edicao de regras nivel 1;
- ajuste visual de intervalo;
- exportacao CSV especifica da tabela nivel 1;
- modo avancado separado usando o monitor antigo por janela ativa.
