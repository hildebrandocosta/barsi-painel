"""
update.py v2 — Atualização Trimestral do Barsi 50
==================================================
Roda uma vez por trimestre (junto com os balanços).
O que faz:
  1. Busca cotações + fundamentos (LPA, VPA, ROE, P/L, P/VP, DY, margem)
     das 50 ações via brapi.dev
  2. (Opcional) Chama a API da Anthropic para buscar recomendações de analistas
  3. Atualiza barsi-data.json
  4. Faz commit e push automático no GitHub

Como usar:
  python update.py                    # atualização completa
  python update.py --so-cotacoes      # só cotações e fundamentos (sem IA, grátis)
  python update.py --so-recomendacoes # só recomendações (usa Claude API)
  python update.py --ticker PETR4     # atualiza só uma ação
  python update.py --sem-push         # não faz push no GitHub

Pré-requisitos (instalar uma vez):
  pip install requests python-dotenv anthropic
"""

import os, sys, json, time, argparse, subprocess, re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent / ".env")

BRAPI_TOKEN      = os.getenv("BRAPI_TOKEN")
ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY")
JSON_PATH        = Path(__file__).parent.parent / "barsi-data.json"
GITHUB_REPO_PATH = Path(__file__).parent.parent

TICKERS = [
  "BBSE3","CXSE3","PSSA3","IRBR3","ITUB4","ITSA4","BBAS3","SANB11","BBDC4","BPAC11",
  "TAEE11","ISAE4","EGIE3","CMIG4","CPLE6","AXIA3","CPFE3","EQTL3",
  "AURE3","PETR4","PRIO3","SBSP3","SAPR11","CSMG3","VIVT3","TIMS3","B3SA3","TOTS3",
  "MOTV3","ECOR3","RAIL3","VBBR3","UGPA3","RENT3","MDIA3","ABEV3","GRND3","FLRY3",
  "HAPV3","HYPE3","ALOS3","MULT3","IGTI11","CURY3","DIRR3","CYRE3","POMO4","WEGE3",
]

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
    log(f"barsi-data.json salvo: {JSON_PATH.stat().st_size:,} bytes", "💾")

# ─── 1. COTAÇÕES + FUNDAMENTOS via brapi.dev ──────────────────────────────────
def atualizar_fundamentos(data, tickers=None):
    import requests
    tickers = tickers or TICKERS
    log(f"Buscando cotações e fundamentos de {len(tickers)} ações...", "📡")

    acoes_map = {a["ticker"]: a for a in data["acoes"]}
    atualizados = 0
    erros = []

    for ticker in tickers:  # 1 por vez — plano gratuito da brapi
        url = f"https://brapi.dev/api/quote/{ticker}"
        params = {"token": BRAPI_TOKEN}
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 401:
                log("BRAPI_TOKEN inválido! Configure no .env", "❌")
                break
            if not r.ok:
                erros.append(ticker); continue

            results = r.json().get("results", [])
            if not results:
                erros.append(ticker); continue
            res = results[0]

            a = acoes_map.get(ticker)
            if not a:
                continue

            # ── Cotação ──────────────────────────────────────────────────────
            preco = res.get("regularMarketPrice")
            if preco and preco > 0:
                a["cotacao"]    = round(preco, 2)
                a["cotacaoRef"] = round(preco, 2)

            # ── P/L direto + LPA ─────────────────────────────────────────────
            pe  = res.get("priceEarnings")
            eps = res.get("earningsPerShare")
            if eps and eps != 0:
                a["lpa"] = round(float(eps), 4)          # LPA (base p/ recálculo dinâmico)
                if preco:
                    a["pl"] = round(preco / eps, 1)
            elif pe and pe > 0:
                a["pl"]  = round(float(pe), 1)
                if preco:
                    a["lpa"] = round(preco / pe, 4)

            # ── Módulos: P/VP, VPA, ROE, margem ─────────────────────────────
            stats   = res.get("defaultKeyStatistics") or {}
            findata = res.get("financialData") or {}

            book = stats.get("bookValue")                # VPA direto
            if book and book > 0:
                a["vpa"] = round(float(book), 4)
                if preco:
                    a["pvp"] = round(preco / book, 1)
            else:
                ptb = stats.get("priceToBook")
                if ptb and ptb > 0:
                    a["pvp"] = round(float(ptb), 1)
                    if preco:
                        a["vpa"] = round(preco / ptb, 4)

            roe = findata.get("returnOnEquity")
            if roe:
                a["roe"] = round(float(roe) * 100, 1)

            margem = findata.get("profitMargins")
            if margem:
                a["margem"] = round(float(margem) * 100, 1)

            # ── Dividendos → DY ──────────────────────────────────────────────
            div_rate = res.get("dividendRate")           # R$/ação 12m
            if div_rate and div_rate > 0:
                a["dividAnual"] = round(float(div_rate), 2)
                if preco:
                    a["dy"] = round(div_rate / preco * 100, 1)
            else:
                dy_pct = res.get("dividendYield")
                if dy_pct and preco:
                    a["dy"] = round(float(dy_pct), 1)
                    a["dividAnual"] = round(preco * float(dy_pct) / 100, 2)

            atualizados += 1
            log(f"  {ticker}: R${a.get('cotacao','?')} | P/L {a.get('pl','?')} | P/VP {a.get('pvp','?')} | ROE {a.get('roe','?')}% | DY {a.get('dy','?')}%", "✅")

        except Exception as e:
            log(f"  {ticker}: {e}", "⚠️")
            erros.append(ticker)

        time.sleep(0.4)  # rate-limit

    log(f"Fundamentos: {atualizados} atualizados, {len(erros)} erros", "📊")
    if erros:
        log(f"Falhas: {', '.join(erros)} — verifique tickers na brapi", "⚠️")
    return atualizados

# ─── 2. RECOMENDAÇÕES via Claude + web search (opcional) ──────────────────────
def atualizar_recomendacoes(data, tickers=None):
    try:
        import anthropic
    except ImportError:
        log("Pacote 'anthropic' não instalado: pip install anthropic", "❌")
        return 0
    if not ANTHROPIC_KEY:
        log("ANTHROPIC_API_KEY não configurada no .env — pulando recomendações", "⚠️")
        return 0

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    tickers = tickers or TICKERS
    log(f"Buscando recomendações de {len(tickers)} ações via Claude...", "🤖")

    acoes_map = {a["ticker"]: a for a in data["acoes"]}
    atualizados = 0

    for ticker in tickers:
        a = acoes_map.get(ticker)
        if not a: continue
        nome = a.get("nome", ticker)
        log(f"  {ticker} ({nome})...", "🔍")

        prompt = f"""Busque na internet as recomendações MAIS RECENTES de analistas para {ticker} ({nome}) na B3. Retorne SOMENTE JSON válido:
{{"consenso":"COMPRAR|NEUTRO|VENDER","nAnalistas":n,"nComprar":n,"nNeutro":n,"nVender":n,"alvoMedio":n,"alvoMax":n,"alvoMin":n,"cotacaoRef":n,"atualizacao":"mês/ano","casas":[{{"casa":"nome","rec":"COMPRAR|NEUTRO|VENDER","alvo":n,"data":"mês/ano","nota":"1-2 frases"}}]}}
Priorize BTG, XP, Safra, Itaú BBA, Genial, Goldman, JPMorgan. Últimos 6 meses. ATENÇÃO: use preços-alvo na base atual da ação (considere splits/inplits recentes)."""

        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1500,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}]
            )
            texto = "".join(b.text for b in resp.content if hasattr(b, "text"))
            m = re.search(r"\{[\s\S]*\}", texto)
            if not m:
                log(f"  {ticker}: sem JSON", "⚠️"); continue
            rec = json.loads(m.group(0))
            if rec.get("consenso") and rec.get("casas"):
                a["analistas"] = rec
                atualizados += 1
                log(f"  {ticker}: {rec['consenso']} | alvo R${rec.get('alvoMedio','?')}", "✅")
        except Exception as e:
            log(f"  {ticker}: {e}", "⚠️")
        time.sleep(2)

    log(f"Recomendações: {atualizados}/{len(tickers)}", "📊")
    return atualizados

# ─── 3. GIT PUSH ──────────────────────────────────────────────────────────────
def git_commit_push(msg=None):
    if not msg:
        msg = f"update: dados {datetime.now().strftime('%Y-%m-%d')}"
    log(f"Commit e push: '{msg}'", "📤")
    try:
        repo = str(GITHUB_REPO_PATH)
        subprocess.run(["git", "-C", repo, "add", "barsi-data.json"], check=True)
        subprocess.run(["git", "-C", repo, "commit", "-m", msg], check=True)
        subprocess.run(["git", "-C", repo, "push"], check=True)
        log("Push OK!", "✅")
    except subprocess.CalledProcessError as e:
        log(f"Erro git: {e} — faça o push manualmente ou verifique credenciais", "❌")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--so-cotacoes", action="store_true")
    p.add_argument("--so-recomendacoes", action="store_true")
    p.add_argument("--ticker", type=str)
    p.add_argument("--sem-push", action="store_true")
    args = p.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else None

    print("\n" + "="*60)
    print("  BARSI 50 — Atualização de Dados v2")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*60 + "\n")

    data = carregar_json()
    log(f"{len(data['acoes'])} ações | última atualização: {data['meta'].get('atualizacao','?')}")

    fund_ok = rec_ok = 0
    if not args.so_recomendacoes:
        fund_ok = atualizar_fundamentos(data, tickers)
    if not args.so_cotacoes:
        rec_ok = atualizar_recomendacoes(data, tickers)

    salvar_json(data)

    if not args.sem_push:
        partes = []
        if fund_ok: partes.append(f"fundamentos ({fund_ok})")
        if rec_ok:  partes.append(f"recomendações ({rec_ok})")
        git_commit_push("update: " + " + ".join(partes) if partes else None)

    print("\n" + "="*60)
    print(f"  ✅ Concluído! Fundamentos: {fund_ok} | Recomendações: {rec_ok}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
