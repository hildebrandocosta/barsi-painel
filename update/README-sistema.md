Barsi 50 — Sistema
Painel fundamentalista com atualização trimestral automática.
Estrutura do repositório
```
barsi-painel/           ← repositório GitHub Pages (já existe)
├── index.html          ← painel (visual idêntico ao atual)
├── barsi-data.json     ← dados das 50 ações (atualizado trimestralmente)
└── update/
    ├── update.py       ← script de atualização trimestral
    ├── requirements.txt
    └── .env            ← suas chaves de API (NÃO sobe para o GitHub)
```
Instalação (uma única vez)
```bash
# 1. Na pasta do repositório barsi-painel clonado no seu PC:
cd C:\Projetos\barsi-painel

# 2. Criar pasta update e copiar os arquivos
mkdir update
# (copiar update.py, requirements.txt para a pasta update/)

# 3. Instalar dependências
pip install -r update/requirements.txt

# 4. Criar arquivo .env na pasta update/
# (copiar .env.example e preencher com suas chaves)
```
Arquivo .env (criar em update/.env)
```
ANTHROPIC_API_KEY=sk-ant-...
BRAPI_TOKEN=seu_token_brapi
```
Uso trimestral
```bash
# Atualização completa (cotações + recomendações + push GitHub)
python update/update.py

# Só cotações (rápido, ~2 min, sem custo de IA)
python update/update.py --so-cotacoes

# Só recomendações (usa Claude, ~15 min)
python update/update.py --so-recomendacoes

# Atualizar só uma ação
python update/update.py --ticker PETR4

# Testar sem fazer push
python update/update.py --sem-push
```
Fluxo trimestral recomendado
Resultado dos balanços sai (jan, abr, jul, out)
Você abre o terminal na pasta do projeto
Roda `python update/update.py`
Aguarda ~15 minutos (cotações + recomendações de 50 ações)
Push automático no GitHub
Painel atualizado em 2 minutos
Custo estimado por atualização trimestral
Cotações (brapi.dev): gratuito
Recomendações (Claude API, 50 ações): ~$0.50 USD (~R$2,50)
Hospedagem (GitHub Pages): gratuito
Total anual: ~$2 USD (~R$10)
