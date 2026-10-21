# 📊 Barsi 50 — Painel Fundamentalista

Dashboard interativo para análise fundamentalista de 48 ações da B3, baseado na metodologia de investimento em dividendos de **Luiz Barsi Filho** e no método de preço justo de **Décio Bazin**.

🔗 **Acesse o painel:** [hildebrandocosta.github.io/barsi-painel](https://hildebrandocosta.github.io/barsi-painel/)

---

## ✨ Funcionalidades

- **48 ações pré-selecionadas** de setores perenes: bancos, seguros, energia elétrica, transmissão, saneamento, telecom, infraestrutura financeira, concessões, consumo não-cíclico, saúde, shoppings e industriais
- **Cotações ao vivo** via API [brapi.dev](https://brapi.dev), atualizadas a cada acesso
- **Metodologia Barsi/Bazin em 6 etapas**, com veredicto automático (Comprar / Comprar c/ Atenção / Aguardar / Evitar) para cada ação
- **Indicadores fundamentalistas**: P/L, P/VP, ROE, Dividend Yield, Dívida/EBITDA, Margem Líquida, CAGR de Lucro
- **Cálculo do Preço Justo** pelo método Bazin (dividendo anual ÷ 6%)
- **Gráficos históricos** de DY e cotação indexada (2020–2026)
- **Comparativo setorial** entre ações do mesmo segmento
- Filtros por setor, recomendação, busca por ticker/nome e ordenação por múltiplos critérios

---

## 🚀 Como usar

1. Acesse o link do painel acima
2. Use a barra lateral para buscar, filtrar e ordenar as 48 ações
3. Clique em uma ação para ver a análise completa nas abas: **Análise Barsi**, **Gráficos**, **Indicadores** e **Resumo**
4. Clique no ícone **⚙️** para configurar seu token gratuito da [brapi.dev](https://brapi.dev) e habilitar cotações em tempo real
5. Adicione à tela inicial do celular (Safari → Compartilhar → Adicionar à Tela de Início) para acesso rápido como um app

---

## 🛠️ Tecnologia

- HTML, CSS e JavaScript puro (sem frameworks ou build steps)
- [Chart.js](https://www.chartjs.org/) para visualização de dados
- Hospedado gratuitamente via GitHub Pages
- Cotações em tempo real via [brapi.dev](https://brapi.dev) (API pública e gratuita de dados da B3)

---

## ⚠️ Aviso importante

Este painel tem caráter **educacional e informativo**. As recomendações geradas (Comprar/Aguardar/Evitar) são baseadas em regras objetivas aplicadas a indicadores históricos e **não constituem recomendação de investimento**. Rentabilidade passada não garante resultados futuros. Consulte um profissional certificado antes de tomar decisões de investimento.

---

## 📚 Fontes de dados

Indicadores fundamentalistas consolidados a partir de StockAnalysis, StatusInvest, Investidor10, Suno Research, BTG Pactual Research e XP Investimentos (referência: jun/2026).

## Revisão de 21/10/2026

O universo efetivo é de **48 ações** (o nome histórico “Barsi 50” não indica a contagem).
CPLE6 foi substituída por CPLE3, conforme a migração da Copel para o Novo Mercado:
https://www.copel.com/site/noticias/copel-ingressa-no-rol-das-empresas-com-padroes-mais-elevados-de-governanca-corporativa/
Os dados por ação da Copel permanecem legados e bloqueados para compra automática até reconciliação.

O veredicto agora usa as mesmas seis etapas exibidas, inclusive preço justo sem tolerância e comparação setorial. Compra exige dados com data comprovada: cotação de até 7 dias e fundamentos de até 120 dias. São limites operacionais deste painel, não critérios atribuídos a Barsi. Fundamentos antigos sem data comprovada não passam por atuais. Os consensos de analistas continuam com suas datas originais e não entram no veredicto automático.

**Não houve atualização validada de preços/fundamentos nesta revisão.** A consulta pública retornou HTTP 429; o acesso direto ao provedor neste ambiente não respondeu. A reserva de 23/07/2026 foi preservada. A data de revisão técnica não é a data de mercado. As demais 47 ações não tiveram sua negociação atual confirmada por resposta do provedor nesta execução.

O atualizador deriva o universo do JSON, pede os módulos de fundamentos explicitamente, valida símbolo/preço/data e não salva nem faz push quando nenhuma consulta tem sucesso. Campos ausentes continuam na reserva; múltiplos e DY são recalculados com a cotação aceita. `fundamentosConsulta` indica consulta ao provedor e não data de balanço. A data `fundamentosData` só deve ser preenchida após conferir o período dos fundamentos e reconciliar eventos corporativos.

Falhas de cotação preservam os valores em memória; falha de carregamento do JSON recupera a última base válida salva neste navegador, quando disponível. As chamadas têm timeout; 401 e 429 interrompem a rodada. Sem token, o provedor só disponibiliza alguns ativos de demonstração, conforme https://brapi.dev/docs/acoes.

Validação: `node tests/painel.test.cjs` e `python -m py_compile update/update.py`.

### Nova tentativa em 21/10/2026

Atualização parcial validada: ITUB4 com cotação de R$48,92 em 21/10/2026 às 14:49:30 UTC; PETR4 com R$48,72 em 28/09/2026 às 23:33:57 UTC. LPA, VPA, ROE e margem foram renovados com os snapshots disponíveis do provedor (06/10 para ITUB4 e 28/09 para PETR4), relativos ao trimestre de 30/06/2026. P/L, P/VP e DY foram recalculados; os dividendos anuais continuam na reserva anterior. A data global da reserva não foi avançada. Os outros 46 ativos não foram renovados; consultas a BBSE3 e CPLE3 não retornaram dados acessíveis. Não há liberação de compra automática com fundamentos parcialmente reconciliados. Fontes e datas por ativo estão no campo `proveniencia`.
