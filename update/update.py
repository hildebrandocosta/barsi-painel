"""
update.py — Atualização Trimestral do Barsi 50
================================================
Roda uma vez por trimestre (junto com os balanços).
O que faz:
  1. Busca cotações e indicadores atuais das 50 ações via brapi.dev
  2. Chama a API da Anthropic (Claude + web search) para buscar recomendações
  3. Atualiza barsi-data.json com os novos dados
  4. Faz commit e push automático no GitHub

Como usar:
  python update.py                    # atualização completa
  python update.py --so-cotacoes      # só cotações (rápido, sem IA)
  python update.py --so-recomendacoes # só recomendações (usa Claude)
  python update.py --ticker PETR4     # atualiza só uma ação

Pré-requisitos:
  pip install requests python-dotenv anthropic
"""

import os, sys, json, time, argparse, subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Configuração ──────────────────────────────────────────────────────────────
BRAPI_TOKEN      = os.getenv("BRAPI_TOKEN")
ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY")
JSON_PATH        = Path(__file__).parent.parent / "barsi-data.json"  # raiz do repo
GITHUB_REPO_PATH = Path(__file__).parent.parent                       # raiz do repo

TICKERS = [
  "BBSE3","CXSE3","PSSA3","IRBR3","ITUB4","ITSA4","BBAS3","SANB11","BBDC4","BPAC11",
  "TAEE11","TRPL4","ISAE4","EGIE3","CMIG4","CPLE6","AXIA6","CPFE3","ENBR3","EQTL3",
  "AURE3","PETR4","PRIO3","SBSP3","SAPR11","CSMG3","VIVT3","TIMS3","B3SA3","TOTS3",
  "CCRO3","ECOR3","RAIL3","VBBR3","UGPA3","RENT3","MDIA3","ABEV3","GRND3","FLRY3",
  "HAPV3","HYPE3","ALOS3","MULT3","IGTI11","CURY3","DIRR3","CYRE3","POMO4","WEGE3",
]

# ─── Helpers ───────────────────────────────────────────────────────────────────
def log(msg, emoji="📌"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {emoji} {msg}")

def carregar_json():
    if not JSON_PATH.exists():
        log(f"ERRO: {JSON_PATH} não encontrado!", "❌")
        sys.exit(1)
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)

def salvar_json(data):
    data["meta"]["atualizacao"] = datetime.now().strftime("%Y-%m-%d")
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    size = JSON_PATH.stat().st_size
    log(f"barsi-data.json salvo: {size:,} bytes", "💾")

# ─── 1. COTAÇÕES via brapi.dev ─────────────────────────────────────────────────
def atualizar_cotacoes(data, tickers=None):
    import requests
    tickers = tickers or TICKERS
    log(f"Buscando cotações de {len(tickers)} ações via brapi.dev...", "📡")

    acoes_map = {a["ticker"]: a for a in data["acoes"]}
    atualizados = 0
    erros = []

    CHUNK = 5  # brapi gratuito: poucos tickers por requisição
    for i in range(0, len(tickers), CHUNK):
        lote = tickers[i:i+CHUNK]
        url  = f"https://brapi.dev/api/quote/{','.join(lote)}"
        params = {"token": BRAPI_TOKEN, "modules": "defaultKeyStatistics,financialData"}

        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 401:
                log("BRAPI_TOKEN inválido ou expirado! Configure no .env", "❌")
                break
            if not r.ok:
                log(f"Erro brapi lote {lote}: HTTP {r.status_code}", "⚠️")
                erros.extend(lote)
                continue

            results = r.json().get("results", [])
            for res in results:
                ticker = res.get("symbol")
                if ticker not in acoes_map:
                    continue
                a = acoes_map[ticker]

                # Cotação
                preco = res.get("regularMarketPrice")
                if preco:
                    a["cotacao"] = round(preco, 2)
                    a["cotacaoRef"] = round(preco, 2)

                # DY trailing 12m
                dy = res.get("dividendYield")
                if dy and isinstance(dy, (int, float)):
                    a["dy"] = round(float(dy), 1)

                # P/L
                pe = res.get("priceEarnings")
                if pe and isinstance(pe, (int, float)):
                    a["pl"] = round(float(pe), 1)

                # P/VP e outros via módulos
                stats = res.get("defaultKeyStatistics", {}) or {}
                findata = res.get("financialData", {}) or {}

                pvp = stats.get("priceToBook") or findata.get("priceToBook")
                if pvp:
                    a["pvp"] = round(float(pvp), 1)

                roe = findata.get("returnOnEquity")
                if roe:
                    a["roe"] = round(float(roe) * 100, 1)

                margem = findata.get("profitMargins")
                if margem:
                    a["margem"] = round(float(margem) * 100, 1)

                # dividAnual
                div_anual = res.get("dividendRate")
                if div_anual:
                    a["dividAnual"] = round(float(div_anual), 2)

                atualizados += 1
                log(f"  {ticker}: R${a['cotacao']} | DY:{a['dy']}% | P/L:{a['pl']}x", "✅")

        except Exception as e:
            log(f"Erro no lote {lote}: {e}", "⚠️")
            erros.extend(lote)

        time.sleep(0.3)  # respeitar rate limit

    log(f"Cotações: {atualizados} atualizadas, {len(erros)} erros", "📊")
    if erros:
        log(f"Falhas: {', '.join(erros)}", "⚠️")
    return atualizados

# ─── 2. RECOMENDAÇÕES via Claude + web search ──────────────────────────────────
def atualizar_recomendacoes(data, tickers=None):
    try:
        import anthropic
    except ImportError:
        log("Pacote 'anthropic' não instalado. Execute: pip install anthropic", "❌")
        return 0

    if not ANTHROPIC_KEY:
        log("ANTHROPIC_API_KEY não configurada no .env", "❌")
        return 0

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    tickers = tickers or TICKERS
    log(f"Buscando recomendações de {len(tickers)} ações via Claude...", "🤖")

    acoes_map = {a["ticker"]: a for a in data["acoes"]}
    atualizados = 0

    for ticker in tickers:
        if ticker not in acoes_map:
            continue
        a = acoes_map[ticker]
        nome = a.get("nome", ticker)

        log(f"  Buscando recomendações para {ticker} ({nome})...", "🔍")

        prompt = f"""Busque na internet as recomendações MAIS RECENTES de analistas de investimento para a ação {ticker} ({nome}) na B3.

Retorne SOMENTE um JSON válido, sem texto adicional, sem markdown:
{{
  "consenso": "COMPRAR" ou "NEUTRO" ou "VENDER",
  "nAnalistas": total,
  "nComprar": qtd,
  "nNeutro": qtd,
  "nVender": qtd,
  "alvoMedio": número,
  "alvoMax": número,
  "alvoMin": número,
  "cotacaoRef": número,
  "atualizacao": "mês/ano ex: jun/2026",
  "casas": [
    {{"casa": "nome", "rec": "COMPRAR/NEUTRO/VENDER/MANTER", "alvo": número ou null, "data": "mês/ano", "nota": "1-2 frases"}}
  ]
}}

Priorize: BTG, XP, Safra, Itaú BBA, Genial, Goldman, JPMorgan, Morgan Stanley, Bradesco BBI, BB Investimentos. Últimos 6 meses."""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )

            texto = "".join(
                b.text for b in response.content
                if hasattr(b, "text")
            )

            match = __import__("re").search(r"\{[\s\S]*\}", texto)
            if not match:
                log(f"  {ticker}: sem JSON na resposta", "⚠️")
                continue

            rec = json.loads(match.group(0))
            if not rec.get("consenso") or not rec.get("casas"):
                log(f"  {ticker}: JSON incompleto", "⚠️")
                continue

            a["analistas"] = rec
            atualizados += 1
            log(f"  {ticker}: {rec['consenso']} | {rec['nAnalistas']} analistas | alvo R${rec.get('alvoMedio','?')}", "✅")

        except json.JSONDecodeError as e:
            log(f"  {ticker}: erro ao parsear JSON: {e}", "⚠️")
        except Exception as e:
            log(f"  {ticker}: erro: {e}", "⚠️")

        time.sleep(2)  # pausa entre chamadas à API

    log(f"Recomendações: {atualizados}/{len(tickers)} atualizadas", "📊")
    return atualizados

# ─── 3. COMMIT e PUSH no GitHub ────────────────────────────────────────────────
def git_commit_push(mensagem=None):
    if not mensagem:
        hoje = datetime.now().strftime("%Y-%m-%d")
        mensagem = f"update: dados trimestrais {hoje}"

    log(f"Fazendo commit e push: '{mensagem}'", "📤")
    try:
        repo = GITHUB_REPO_PATH
        subprocess.run(["git", "-C", str(repo), "add", "barsi-data.json"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", mensagem], check=True)
        subprocess.run(["git", "-C", str(repo), "push"], check=True)
        log("Push realizado com sucesso!", "✅")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Erro no git: {e}", "❌")
        log("Verifique se o repositório está configurado e autenticado.", "💡")
        return False

# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Atualização Trimestral Barsi 50")
    parser.add_argument("--so-cotacoes",      action="store_true", help="Só atualiza cotações")
    parser.add_argument("--so-recomendacoes", action="store_true", help="Só atualiza recomendações")
    parser.add_argument("--ticker",           type=str,            help="Atualiza só um ticker ex: PETR4")
    parser.add_argument("--sem-push",         action="store_true", help="Não faz push no GitHub")
    args = parser.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else None

    print("\n" + "="*60)
    print("  BARSI 50 — Atualização Trimestral")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*60 + "\n")

    data = carregar_json()
    log(f"Dados carregados: {len(data['acoes'])} ações | última atualização: {data['meta'].get('atualizacao','?')}")

    cotacoes_ok = 0
    recomendacoes_ok = 0

    if not args.so_recomendacoes:
        cotacoes_ok = atualizar_cotacoes(data, tickers)

    if not args.so_cotacoes:
        recomendacoes_ok = atualizar_recomendacoes(data, tickers)

    salvar_json(data)

    if not args.sem_push:
        partes = []
        if cotacoes_ok:       partes.append(f"cotações ({cotacoes_ok})")
        if recomendacoes_ok:  partes.append(f"recomendações ({recomendacoes_ok})")
        msg = "update: " + " + ".join(partes) if partes else "update: dados trimestrais"
        git_commit_push(msg)
    else:
        log("Push ignorado (--sem-push). Arquivo salvo localmente.", "💡")

    print("\n" + "="*60)
    print(f"  ✅ Concluído! Cotações: {cotacoes_ok} | Recomendações: {recomendacoes_ok}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
