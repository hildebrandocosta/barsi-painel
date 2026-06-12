# 📊 Barsi 50 — Painel Fundamentalista

Dashboard interativo para análise fundamentalista de 50 ações da B3, baseado na metodologia de investimento em dividendos de **Luiz Barsi Filho** e no método de preço justo de **Décio Bazin**.

🔗 **Acesse o painel:** [hildebrandocosta.github.io/barsi-painel](https://hildebrandocosta.github.io/barsi-painel/)

---

## ✨ Funcionalidades

- **50 ações pré-selecionadas** de setores perenes: bancos, seguros, energia elétrica, transmissão, saneamento, telecom, infraestrutura financeira, concessões, consumo não-cíclico, saúde, shoppings e industriais
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
2. Use a barra lateral para buscar, filtrar e ordenar as 50 ações
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
