# Instruções para a exportação UFPR

## Objetivo e escopo

`scripts/export_ufpr_data.py` produz um JSON consolidado para análise da preparação UFPR a partir do SQLite local do Routine IA. Mantenha este fluxo aditivo e compatível: ele não deve alterar rotas, `app.py`, o esquema SQLite ou os dados históricos.

## Regras obrigatórias

- Abra a fonte com SQLite URI `mode=ro`. Nunca reutilize o exportador para gravar, migrar, limpar ou corrigir o banco.
- Use `backend.paths.get_database_path()` e `get_exports_dir()` para os caminhos padrão; não use caminhos relativos para o banco persistente.
- Antes de mudar o mapeamento, confira a tabela e a API que escrevem o campo. Não crie campos, valores padrão ou associações acadêmicas que não existam na fonte.
- Preserve `source_id`, `null` e os valores originais. Campos derivados devem ter nome claro, fórmula documentada e teste/validação correspondente.
- A classificação acadêmica é deliberadamente estrita: apenas `study` e `estudo` em campos estruturados. Não deduza estudo pelo título, nota, app ou texto livre.
- Não inclua `app_usage_events.window_title`, `executable_path`, configurações, backups, chaves ou outros dados pessoais que não contribuam à análise acadêmica.
- Atualize `docs/EXPORTACAO_UFPR.md` no mesmo conjunto de mudanças quando uma seção, fonte, transformação ou limitação mudar.

## Validação mínima

Após modificar o exportador, execute:

```powershell
py -3.14 -m py_compile scripts/export_ufpr_data.py
py -3.14 scripts/export_ufpr_data.py
```

Confirme que o JSON contém `validacao.resultado = "aprovado"`, que o SQLite passa em `PRAGMA integrity_check` e que as contagens detalhadas continuam coerentes com a fonte. Para testes que inicializam o app, use um `ROUTINE_IA_DATA_DIR` temporário, nunca a base pessoal.
