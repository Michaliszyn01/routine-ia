# Exportação UFPR

`scripts/export_ufpr_data.py` gera uma fonte JSON para um projeto do ChatGPT voltado à preparação para a UFPR. O script é aditivo: ele não altera `app.py`, rotas, tabelas, modelos nem qualquer registro histórico. O SQLite é aberto em modo somente leitura (`mode=ro`).

## Como gerar

No diretório `routine_ia`:

```powershell
py -3.14 scripts/export_ufpr_data.py
```

O destino padrão é:

```text
%LOCALAPPDATA%\RoutineIA\exports\routine_ia_ufpr_export.json
```

Também é possível escolher explicitamente a fonte e o destino:

```powershell
py -3.14 scripts/export_ufpr_data.py --database "C:\Users\Eduardo\AppData\Local\RoutineIA\routine.db" --output "C:\Users\Eduardo\Desktop\ufpr.json"
```

Envie somente o JSON final ao projeto do ChatGPT. Ele contém dados pessoais de rotina, desempenho e uso de aplicativos.

## Fonte, transformação e escopo

| Seção JSON | Tabela(s) de origem | Transformação aplicada |
| --- | --- | --- |
| `metas_academicas` | `goals`, `life_goals` | Inclui somente linhas cuja `category` ou `linked_area` seja exatamente `study` ou `estudo`. Mantém as metas atuais; não há histórico de versões de metas no banco. |
| `contexto_diario` | `daily_records`, `health_sleep_daily`, `health_data`, `study_sessions`, `focus_sessions`, `monitoring_app_usage_daily` | Une os dados por `data` em uma linha única. O sono prioritário é `health_sleep_daily`, depois `health_data`, depois o registro manual. Os valores das três fontes continuam explícitos. Totais de estudo, foco e uso do PC são calculados a partir das linhas daquela data. |
| `sessoes_estudo` | `study_sessions` | Cópia estruturada de matéria, tópico, duração, questões, acertos e erros. `taxa_acerto_percentual` é derivada de `acertos / questoes_resolvidas`; quando não há denominador, vale `null`. |
| `simulados` | `mock_exams` | Cópia estruturada das medidas do simulado. A taxa usa `acertos / total_questoes` quando o total existe. |
| `erros_estudo_e_revisoes` | `study_errors`, `study_review_queue` | Cada erro aparece uma vez e recebe, quando existente, sua fila de revisão pelo `study_error_id`. |
| `sessoes_foco` | `focus_sessions`, `focus_app_usage` | Preserva horários, segundos focados/distraídos e o uso agregado de apps por sessão. `classificada_como_estudo` só é verdadeira com `focus_type` ou `category` exatamente `study`/`estudo`; não há inferência pelo título. |
| `uso_pc_diario` | `monitoring_app_usage_daily` | Agrega por dia e rótulo, mantendo o detalhe por aplicativo. `Produtivo`, `Projeto` e `Estudo` entram no total produtivo; `Risco` e `Distracao` entram no total de risco/distração. Não exporta `window_title`, caminho de executável ou eventos brutos. |
| `planejamento_academico` | `weekly_plan_items`, `daily_plan_blocks`, `daily_plans` | Inclui itens/blocos com categoria ou tipo exatamente `study`/`estudo`; a data de um bloco é obtida do `daily_plans.id`. |
| `habitos_academicos` | `custom_habits`, `habit_logs` | Inclui logs de hábitos cuja categoria da definição seja exatamente `study`/`estudo`. |
| `cobertura_da_fonte` | tabelas acima | Informa contagem e intervalo de datas da fonte, inclusive quando a coleção exportada está vazia. |

Datas permanecem em `YYYY-MM-DD`. Timestamps são padronizados para `YYYY-MM-DDTHH:MM:SS` quando a fonte usa espaço entre data e hora. O banco não guarda fuso horário nesses campos; o exportador não inventa um.

Valores ausentes viram `null`; não são trocados por zero. Zeros existentes na fonte são preservados. Os identificadores `source_id` permitem conferir cada item detalhado contra o SQLite.

## Estrutura resumida

```json
{
  "formato": "routine_ia_ufpr_export",
  "versao_esquema": "1.0",
  "contexto_diario": [
    {
      "data": "2026-07-01",
      "rotina": {"horas_estudo_registro_diario": 2.0, "energia": 3},
      "sono": {"horas_prioritarias": 7.5, "fonte_prioritaria": "health_sleep_daily"},
      "estudos_por_sessao": {"quantidade_sessoes": 1, "taxa_acerto_percentual": 80.0},
      "foco": {"segundos_focados": 1500, "segundos_distraidos": 120},
      "uso_pc": {"segundos_produtivos": 3600, "segundos_risco_distração": 300}
    }
  ],
  "sessoes_estudo": [
    {
      "source_id": 12,
      "data": "2026-07-01",
      "materia": "Matemática",
      "duracao_minutos": 60,
      "questoes_resolvidas": 20,
      "acertos": 16,
      "taxa_acerto_percentual": 80.0
    }
  ]
}
```

O exemplo é apenas contratual: não representa dados presentes no banco.

## Validação

Antes de gravar o arquivo, o script:

1. abre o banco em modo somente leitura e exige as tabelas usadas;
2. executa `PRAGMA integrity_check`;
3. verifica IDs únicos nas coleções detalhadas;
4. compara a quantidade exportada de sessões, simulados, erros e foco com a origem;
5. compara todos os IDs de uso do PC e de uso de apps durante foco com a origem;
6. confirma que as datas de `contexto_diario` são exatamente a união das fontes selecionadas e que não se repetem;
7. compara os IDs das metas acadêmicas com a origem;
8. lê novamente o JSON final e exige o resultado de validação aprovado.

Qualquer falha interrompe o processo com código diferente de zero. A seção `validacao` do JSON registra as checagens concluídas.

## Limitações conhecidas

- A exportação só inclui o que foi efetivamente registrado no Routine IA. Campos e coleções vazias não recebem estimativas.
- O banco atual não possui sessões de estudo, simulados, erros de estudo, metas de vida, planejamento acadêmico ou hábitos acadêmicos preenchidos; as respectivas coleções saem vazias, como sinalização de ausência de dados, não como falha.
- `daily_records.study_hours` é um lançamento diário manual e pode não coincidir com a soma de `study_sessions.duration_minutes`; os dois são mantidos porque medem registros diferentes.
- O sistema não associa automaticamente uma sessão de foco genérica a uma matéria. A exportação não deduz essa relação pelo título.
- O monitoramento do PC fornece contexto de produtividade/distração, mas não prova estudo acadêmico. Eventos brutos e títulos de janela ficam fora por não serem necessários ao objetivo e por privacidade.
- `goals` guarda o estado atual da meta, não seu histórico. Portanto não é possível reconstituir metas que foram alteradas no passado.

## Arquitetura relacionada

- O caminho persistente é definido em `backend/paths.py` (`%LOCALAPPDATA%\RoutineIA\routine.db` e `exports`).
- O esquema inicial e as tabelas legadas ficam em `backend/database.py`; mudanças incrementais de foco, monitoramento e planejamento ficam nos repositórios em `core/tools/`.
- As APIs que registram e leem estudos ficam em `app.py` (`/api/studies*`), foco em `/api/focus*`, rotina em `/api/daily`, metas em `/api/goals` e monitoramento em `/api/monitoring-level1/*`.
- Os CSVs existentes em `backend/export.py` atendem áreas isoladas. Esta exportação é independente e consolidada para análise acadêmica.
