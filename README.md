# Barsi — Painel Fundamentalista

Painel educacional de **48 ações**, em HTML/CSS/JavaScript, hospedado no GitHub Pages:
https://hildebrandocosta.github.io/barsi-painel/

## Situação da atualização de 21/10/2026

- Os 48 tickers foram encontrados na listagem pública da brapi, sem duplicatas.
- CPLE6 foi substituída por CPLE3. Os fundamentos por ação e históricos legados da Copel permanecem pendentes de reconciliação e bloqueados para compra automática. A fonte da conversão é a própria companhia: https://www.copel.com/site/noticias/copel-ingressa-no-rol-das-empresas-com-padroes-mais-elevados-de-governanca-corporativa/
- Os **48 preços disponíveis** foram renovados a partir de https://brapi.dev/api/quote/list, consultada em 21/10/2026. Esse endpoint não informa a data individual de pregão. Nos 46 ativos sem resposta individual datada, `cotacaoData` permanece nula e `cotacaoConsulta` registra a consulta; esses preços não são rotulados como cotações ao vivo.
- ITUB4 e PETR4 tiveram também resposta individual com timestamp de **21/10/2026 às 21:30:30 UTC** (18:30:30 de Brasília). Preços: R$48,90 e R$57,75, respectivamente.
- LPA, VPA, ROE e margem disponíveis de ITUB4 e PETR4 foram renovados com os snapshots de 06/10/2026 e 28/09/2026, referentes a 30/06/2026. As fontes, períodos e datas constam em `proveniencia` e `camposData` no JSON. LPA também foi confirmado na resposta individual de 21/10.
- Dividendos anuais, histórico, CAGR e outros fundamentos não retornados permanecem na reserva anterior. **Atualizar a cotação não renova esses fundamentos.** P/L, P/VP e DY são recalculados com as bases disponíveis, que podem ser legadas. Não foi derivado dividendo anual a partir de um yield cuja unidade/base não foi reconciliada.
- A data global `meta.atualizacao` continua indicando a reserva original de 23/07/2026. A cobertura da revisão atual está em `meta.atualizacaoParcial`.

## Lógica das recomendações

O veredicto usa exatamente as seis etapas exibidas: DY ≥ 6%, setor perene, ROE ≥ 15%, preço ≤ preço Bazin (dividendo anual / 0,06), recorrência conforme histórico e comparação setorial. Cinco etapas, com DY e ROE mínimos, permitem COMPRAR; quatro permitem COMPRAR C/ ATENÇÃO; três levam a AGUARDAR; abaixo disso, EVITAR.

A verificação de dados antecede o veredicto: sem cotação datada de até 7 dias, fundamentos reconciliados de até 120 dias ou com revisão pendente, o resultado é AGUARDAR. Esses prazos são limites operacionais deste painel, não regras atribuídas a Barsi. `fundamentosData` só deve ser preenchida após conferir o período dos fundamentos, os proventos e eventos corporativos; a presença de módulos na resposta não libera compra por si só. A revisão atual ainda não libera compras automáticas.

Os consensos de analistas possuem datas próprias e não alimentam o veredicto. Textos qualitativos e séries históricas não foram renovados nesta revisão e devem ser interpretados como material legado. Proventos futuros não são garantidos.

## Falhas e dados de reserva

Erros HTTP 401/429, timeout, resposta vazia, símbolo divergente, preço inválido ou timestamp inválido/futuro não substituem uma cotação válida. Cotações datadas mais antigas que a reserva também são rejeitadas. O último preço datado aceito fica salvo no navegador e pode ser recuperado após uma falha.

Se o JSON principal falhar, o painel tenta a última base válida salva no navegador. Sem base válida, exibe mensagem explícita e não calcula recomendações. Os dados não dependem de Chart.js para carregar a lista; falha no CDN afeta os gráficos.

Sem token, a consulta individual se limita aos tickers de demonstração liberados pelo provedor. Um token pode ser configurado em ⚙️, ficando apenas no navegador e sendo enviado à brapi pelo cabeçalho Authorization. Restrições do plano podem impedir fundamentos mesmo com token. Documentação: https://brapi.dev/docs/acoes.

## Atualização local

```bash
python update/update.py --so-cotacoes --sem-push
python update/update.py --ticker ITUB4 --so-cotacoes --sem-push
```

As cotações usam a biblioteca padrão do Python. Para carregar `update/.env`, instale `python-dotenv`, ou configure `BRAPI_TOKEN` no ambiente. A consulta opcional a consensos de analistas mantém a integração preexistente com Anthropic e requer chave/pacote próprios; não é necessária para atualizar preços.

O script deriva o universo do JSON, solicita módulos explicitamente, tenta cotação básica quando o plano não permite módulos e interrompe em 401/429. Campos ausentes são preservados, zeros legítimos são aceitos e múltiplos são recalculados. Uma oscilação de base superior a 2x abre revisão de eventos corporativos, sem ajustar automaticamente séries antigas. A gravação do JSON é atômica; nenhuma consulta aceita significa nenhum arquivo salvo nem push.

O comando sem `--sem-push` conserva o comportamento existente de commit/push. Não há atualização agendada configurada no repositório.

## Validação

```bash
node tests/painel.test.cjs
node tests/render.test.cjs
python -m unittest discover -s tests -p 'test_*.py'
python -m py_compile update/update.py
```

Uso informativo e educacional. O painel não substitui análise dos documentos das companhias e não constitui recomendação profissional de investimento.

Foram verificadas 240 renderizações das cinco abas, os filtros/lista e a recuperação da base por cache, em execução JavaScript simulada. Não houve inspeção visual em navegador: o download do Chromium não estava disponível neste ambiente.
