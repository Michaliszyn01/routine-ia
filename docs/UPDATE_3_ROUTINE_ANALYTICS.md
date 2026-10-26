# Update 3 - Routine Analytics

Esta update cria o primeiro cruzamento entre saude, monitoramento do PC, produtividade e rotina diaria.

## Objetivo

Responder perguntas simples de rotina:

- Durmo melhor nos dias em que treino?
- Meu foco melhora quando durmo mais?
- Uso mais apps de risco quando durmo pouco?
- Tenho mais produtividade em dias com treino?
- Quais dias combinam sono bom, treino e foco?
- Quais padroes aparecem nos ultimos 7, 14 e 30 dias?

Os resultados sao pistas de rotina e bem-estar. O Routine IA nao faz diagnostico medico.

## Ferramenta interna

A Update 3 adiciona:

```txt
core/tools/routine_analytics/
  analytics_repository.py
  analytics_service.py
  correlation_engine.py
  insight_rules.py
  analytics_schemas.py
```

Responsabilidades:

- `analytics_repository.py`: le dados de saude, monitoramento e registros diarios.
- `correlation_engine.py`: calcula medias, comparacoes, tendencias e correlacoes simples.
- `insight_rules.py`: transforma sinais em frases simples e nao medicas.
- `analytics_service.py`: monta a resposta final da API.

## Tela

A nova tela fica em:

```txt
/analytics
```

Ela mostra:

- cards de sono medio, tempo produtivo, apps de risco e dias bons combinados;
- insights simples;
- tendencias basicas por metade do periodo;
- correlacoes do periodo;
- tabela diaria combinada.

## API

```txt
GET /api/routine-analytics?period=7
GET /api/routine-analytics?period=14
GET /api/routine-analytics?period=30
```

Tambem aceita `date=YYYY-MM-DD` para testes ou consulta de um periodo encerrando em uma data especifica.

## Dados usados

Saude:

- sono importado;
- passos importados;
- treino importado;
- frequencia cardiaca media, quando existir.

Monitoramento:

- tempo produtivo;
- tempo neutro;
- tempo em apps de risco;
- score simples por categoria.

Rotina diaria:

- score diario;
- treino manual;
- sono manual;
- passos manuais;
- energia e humor.

## Regras simples

- Sono bom: pelo menos 7 horas.
- Sono curto: menos de 6 horas.
- Dia com treino: treino importado ou treino registrado manualmente.
- Foco bom: tempo produtivo maior ou igual ao tempo de risco.
- Risco alto: pelo menos 60 minutos em apps de risco ou risco maior que produtividade.
- Dia bom combinado: sono bom, treino e foco bom no mesmo dia.

## Limites atuais

- Nao usa IA coach.
- Nao faz planejamento automatico.
- Nao faz recomendacao medica.
- Nao bloqueia apps.
- Nao usa machine learning.
- Nao faz predicao avancada.
- Nao adiciona nova integracao com Samsung Health.

## Futuras updates

Futuras versoes podem adicionar graficos melhores, filtros por semana, comparacoes mais detalhadas e sugestoes de rotina, mantendo a separacao entre pistas de rotina e analise medica.

