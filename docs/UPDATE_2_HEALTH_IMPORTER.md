# Update 2 - Health Sync Importer

Esta update cria a primeira versao estavel do importador local de dados de saude.

## Fluxo suportado

```text
Galaxy Watch
-> Samsung Health
-> Health Sync
-> Google Drive
-> Google Drive Desktop no PC
-> Routine IA le as pastas locais sincronizadas
```

O Routine IA nao usa API do Google Drive nesta versao. Ele apenas le arquivos locais dentro da pasta sincronizada pelo Google Drive Desktop.

## Configuracao

A configuracao fica no SQLite local, junto das demais preferencias do app:

```text
health_sync_base_path = G:\Meu Drive
health_auto_import_enabled = true
health_import_interval_hours = 4
```

O caminho pode ser alterado em:

- `GET /health`, no painel Health Sync / Google Drive local;
- `GET /settings`, em Pasta base Health Sync.

## Pastas usadas

Dentro da pasta base, a Update 2 procura somente:

```text
Health Sync Dormir
Health Sync Passos
Health Sync Atividades
Health Sync Frequência Cardíaca
```

Nesta versao, o app ignora:

```text
Health Sync Energia queimada
Health Sync Peso
Health Sync VO2 máx
```

Arquivos `.fit` e `.tcx` tambem sao ignorados. O importador le apenas CSV.

## Dados importados

### Sono

Pasta: `Health Sync Dormir`

Colunas esperadas:

- `Data`
- `Hora`
- `Duracao em segundos`
- `Fase do sono`

O app soma fases por dia e grava em `health_sleep_daily`.

### Passos

Pasta: `Health Sync Passos`

Colunas esperadas:

- `Data`
- `Hora`
- `Passos`

O app soma passos por dia e grava em `health_steps_daily`.

### Atividades

Pasta: `Health Sync Atividades`

Colunas esperadas:

- `Aplicacao de origem`
- `Tipo de atividade`
- `Nome da atividade`
- `Data`
- `Hora`
- `Tempo decorrido`
- `Tempo ativo`
- `Distancia (km)`

O app grava atividades em `health_activities`, sem rota, mapa ou analise detalhada.

### Frequencia cardiaca

Pasta: `Health Sync Frequência Cardíaca`

Colunas esperadas:

- `Data`
- `Hora`
- `Frequencia Cardiaca`
- `Origem`

O app nao salva todos os registros brutos de frequencia cardiaca. Ele calcula e salva apenas resumo diario em `health_heart_rate_daily`:

- media;
- minimo;
- maximo;
- quantidade de amostras.

## Deduplicacao

O Health Sync pode gerar arquivos diarios e arquivos de periodo com dados sobrepostos. Por isso a Update 2 nao confia apenas no nome do arquivo.

O importador:

- calcula hash de conteudo do arquivo;
- registra arquivos em `health_imported_files`;
- ignora arquivos ja importados com sucesso;
- deduplica linhas de sono por `date + stage + start_time + duration_seconds`;
- deduplica passos por `date + time + steps`;
- deduplica atividades por `date + start_time + activity_type + elapsed_seconds + distance_km`;
- consolida resumos diarios por data.

Os resumos tambem sao espelhados para `health_data` com fonte `Health Sync`, mantendo compatibilidade com a tela e exportacoes existentes.

## Importacao manual

Na tela `GET /health`, use:

```text
Importar agora
```

A API local equivalente e:

```text
POST /api/health-import/run
```

## Importacao automatica

Quando `health_auto_import_enabled` esta ativo, o app inicia um agendador local junto com o runtime Flask/desktop. O intervalo padrao e de 4 horas.

O agendador usa uma trava interna para evitar duas importacoes simultaneas.

## Logs e erros

O painel de Health Data mostra:

- caminho configurado;
- ultima importacao;
- quantidade de arquivos candidatos e ignorados;
- logs recentes;
- erro amigavel quando a pasta base nao existe.

Exemplo:

```text
Nao encontrei a pasta G:\Meu Drive. Verifique se o Google Drive esta aberto e sincronizado.
```

## Limites desta versao

Ficaram para depois:

- TCX;
- FIT;
- VO2 max avancado;
- calorias detalhadas;
- analise medica;
- Health Connect direto;
- API do Google Drive;
- app Android proprio;
- IA medica;
- recomendacoes clinicas.

Os insights da tela tratam os dados do relogio como pistas de rotina, nao como diagnostico.
