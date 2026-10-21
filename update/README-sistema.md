# Atualizador do painel

Consulte o README da raiz para cobertura, limitações, datas e critérios de recomendação.

O universo vem de `barsi-data.json`; não há lista paralela de tickers. O modo de cotações usa a biblioteca padrão do Python. Instale `python-dotenv` apenas se quiser carregar as credenciais de `update/.env`, ou configure `BRAPI_TOKEN` no ambiente. Nunca inclua tokens no repositório.

```bash
python update/update.py --so-cotacoes --sem-push
python update/update.py --ticker ITUB4 --so-cotacoes --sem-push
```

Sem token, tenta a listagem pública (preços indicativos sem timestamp individual) e os ativos de demonstração permitidos. Com token, consulta cada ticker com os módulos disponíveis no plano e tenta cotação básica se os módulos forem negados. Em 401 ou 429, interrompe; em falha individual, preserva a reserva. Nenhum dado aceito significa nenhum arquivo salvo ou push.

Datas de consulta, datas de pregão e períodos de fundamentos são distintos. Módulos parciais não preenchem `fundamentosData`; liberar compra exige reconciliação. Dividend yield sem unidade/base confirmada não é usado para reconstruir dividendos anuais. O arquivo é gravado por substituição atômica, sem NaN/Infinity.

O comando sem `--sem-push` conserva commit/push automático do script original. Não há agendamento instalado. O modo opcional de consenso de analistas requer `ANTHROPIC_API_KEY` e o pacote `anthropic`; é independente do veredicto do painel.
