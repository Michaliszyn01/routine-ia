# Update 2.2 - Health Data UI

Esta update melhora a tela Health Data sem reimplementar o Health Importer da Update 2.

## Objetivo

Deixar os dados importados pelo Health Sync mais claros, simples e uteis para consulta diaria.

## Cards adicionados

- Sono de hoje, com total, sono leve, sono profundo, REM e tempo acordado.
- Passos de hoje, com comparacao simples em relacao a ontem quando houver dados.
- Ultimo treino, com tipo, data, duracao e distancia quando existir.
- Frequencia cardiaca media do dia, com minima, maxima e quantidade de amostras.

Os valores de frequencia cardiaca sao apenas exibidos. O Routine IA nao faz interpretacao clinica.

## Ultimos 7 dias

A tabela mostra os ultimos 7 dias em ordem do mais recente para o mais antigo.

Colunas:

- Data
- Sono total
- Passos
- Treino
- FC media

Quando algum dado nao existe, a tela exibe `-` e continua funcionando.

## Status da integracao

A tela mostra:

- caminho base configurado;
- status da pasta;
- ultima importacao;
- proxima importacao automatica;
- importacao automatica ativada ou desativada;
- quantidade de arquivos importados;
- quantidade de arquivos ignorados na varredura atual;
- ultimo erro, se existir.

Se a pasta configurada nao existir, a mensagem orienta abrir/sincronizar o Google Drive Desktop.

## Como alterar o caminho base

Na secao Importacao e configuracoes:

1. Edite o campo Alterar caminho base.
2. Use um caminho local existente, por exemplo `G:\Meu Drive`.
3. Clique em Salvar caminho.

O app valida se a pasta existe antes de salvar.

## Importar agora

O botao Importar agora chama a importacao manual do Health Sync.

Depois da importacao, a tela atualiza:

- cards de hoje;
- tabela dos ultimos 7 dias;
- status da integracao;
- logs recentes.

## Importacao automatica

A importacao automatica usa o scheduler local ja existente.

O intervalo configurado define quando a proxima importacao deve acontecer. A tela exibe a proxima execucao quando o scheduler esta ativo.

## Limitacoes atuais

- Apenas arquivos CSV do Health Sync sao lidos.
- Arquivos FIT e TCX continuam ignorados nesta versao.
- Nao ha analise medica.
- Nao ha IA coach.
- Nao ha graficos avancados.
- Nao ha API direta do Google Drive, Health Connect ou app Android.

## Futuras updates

Podem evoluir para graficos, recomendacoes, novas fontes e analises mais completas, mas isso nao faz parte da Update 2.2.
