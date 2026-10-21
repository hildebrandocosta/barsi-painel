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
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args):
        pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent / ".env")

BRAPI_TOKEN      = os.getenv("BRAPI_TOKEN")
ANTHROPIC_KEY    = os.getenv("ANTHROPIC_API_KEY")
JSON_PATH        = Path(__file__).parent.parent / "barsi-data.json"
GITHUB_REPO_PATH = Path(__file__).parent.parent


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
    # Datas dos dados só avançam após resposta válida do provedor.
    tmp = JSON_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
    tmp.replace(JSON_PATH)
    log(f"barsi-data.json salvo: {JSON_PATH.stat().st_size:,} bytes", "💾")

# ─── 1. COTAÇÕES + FUNDAMENTOS via brapi.dev ──────────────────────────────────
def numero(value):
    import math
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def data_iso(value):
    from datetime import timezone
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        dt = dt.replace(tzinfo=dt.tzinfo or timezone.utc)
        return dt if dt <= datetime.now(timezone.utc) else None
    except ValueError:
        return None


def recalcular(a):
    preco = a.get('cotacao')
    if not numero(preco) or preco <= 0:
        return
    for campo, base in [('pl', 'lpa'), ('pvp', 'vpa')]:
        valor = a.get(base)
        a[campo] = round(preco / valor, 2) if numero(valor) and valor != 0 else None
    div = a.get('dividAnual')
    a['dy'] = round(div / preco * 100, 2) if numero(div) and div >= 0 else None


def aplicar_cotacao(a, res):
    """Valida antes de alterar. Data de consulta não equivale a data de pregão."""
    from copy import deepcopy
    if not isinstance(res, dict) or res.get('symbol') != a['ticker']:
        return False
    preco, quando = res.get('regularMarketPrice'), data_iso(res.get('regularMarketTime'))
    anterior = data_iso(a.get('cotacaoData'))
    if not numero(preco) or preco <= 0 or quando is None or (anterior and quando < anterior):
        return False
    novo = deepcopy(a)
    novo.update(cotacao=round(preco, 2), cotacaoRef=round(preco, 2), cotacaoData=res['regularMarketTime'])
    stats = res.get('defaultKeyStatistics')
    stats = stats if isinstance(stats, dict) else {}
    fin = res.get('financialData')
    fin = fin if isinstance(fin, dict) else {}
    datas = novo.setdefault('camposData', {})
    # Nunca transforma uma atualização parcial em fundamentos totalmente atuais.
    campos = {'lpa': res.get('earningsPerShare'), 'vpa': stats.get('bookValue'),
              'roe': fin.get('returnOnEquity'), 'margem': fin.get('profitMargins'),
              'dividAnual': res.get('dividendRate')}
    snapshot = res.get('requestedAt') or res['regularMarketTime']
    periodo = stats.get('mostRecentQuarter')
    for campo, valor in campos.items():
        if not numero(valor) or (campo == 'dividAnual' and valor < 0):
            continue
        campo_anterior = data_iso(datas.get(campo, {}).get('snapshot'))
        if campo_anterior and data_iso(snapshot) and data_iso(snapshot) < campo_anterior:
            continue
        novo[campo] = round(valor * 100 if campo in ('roe', 'margem') else valor, 6)
        datas[campo] = {'snapshot': snapshot, 'periodo': periodo}
    fonte = 'https://brapi.dev/api/quote/' + a['ticker']
    novo.setdefault('proveniencia', {}).update(cotacao=fonte, tipoCotacao='Cotação individual datada')
    if stats or fin:
        novo['fundamentosConsulta'] = snapshot
    if numero(a.get('cotacao')) and (preco / a['cotacao'] > 2 or preco / a['cotacao'] < 0.5):
        novo['revisaoPendente'] = True
        novo['motivoRevisao'] = 'Variação de base superior a 2x: conferir eventos corporativos e fundamentos por ação.'
    recalcular(novo)
    a.clear()
    a.update(novo)
    return True


def aplicar_lista(a, item, consulta):
    """Preço indicativo de listagem sem timestamp individual; não libera compra."""
    from copy import deepcopy
    if item.get('stock') != a['ticker'] or not numero(item.get('close')) or item['close'] <= 0:
        return False
    novo = deepcopy(a)
    fonte = novo.setdefault('proveniencia', {})
    fonte.setdefault('reservaAnterior', {'cotacao': a['cotacao'], 'data': a.get('cotacaoData')})
    if item['close'] / a['cotacao'] > 2 or item['close'] / a['cotacao'] < 0.5:
        novo['revisaoPendente'] = True
        novo['motivoRevisao'] = 'Variação de base superior a 2x: conferir eventos corporativos e fundamentos por ação.'
    novo.update(cotacao=round(item['close'], 2), cotacaoRef=round(item['close'], 2),
                cotacaoData=None, cotacaoConsulta=consulta)
    fonte.update(cotacao='https://brapi.dev/api/quote/list', tipoCotacao='Listagem sem data de pregão individual')
    recalcular(novo)
    a.clear()
    a.update(novo)
    return True


def consultar(url, params=None):
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    if params:
        url += '?' + urlencode(params)
    headers = {'Accept': 'application/json'}
    if BRAPI_TOKEN:
        headers['Authorization'] = 'Bearer ' + BRAPI_TOKEN
    with urlopen(Request(url, headers=headers), timeout=12) as resp:
        return json.load(resp)


def atualizar_fundamentos(data, tickers=None):
    from urllib.error import HTTPError
    selecionados = set(tickers or [a['ticker'] for a in data['acoes']])
    acoes = [a for a in data['acoes'] if a['ticker'] in selecionados]
    alterados = set()
    # Sem token, a listagem pública ainda permite conferir o universo e os preços.
    if not BRAPI_TOKEN:
        try:
            lista = consultar('https://brapi.dev/api/quote/list')
            itens = {i['stock']: i for i in lista.get('stocks', []) if isinstance(i, dict) and 'stock' in i}
            for a in acoes:
                if a['ticker'] in itens and aplicar_lista(a, itens[a['ticker']], datetime.now().strftime('%Y-%m-%d')):
                    alterados.add(a['ticker'])
        except Exception as exc:
            log(f'Listagem indisponível ({type(exc).__name__}); reserva preservada', '⚠️')
    for a in acoes:
        ticker = a['ticker']
        if not BRAPI_TOKEN and ticker not in ('PETR4', 'ITUB4', 'VALE3', 'MGLU3'):
            continue
        url = 'https://brapi.dev/api/quote/' + ticker
        try:
            try:
                payload = consultar(url, {'modules': 'defaultKeyStatistics,financialData'})
            except HTTPError as exc:
                if exc.code not in (400, 402, 403):
                    raise
                payload = consultar(url)  # Plano sem módulos: ainda tenta a cotação básica.
            for res in payload.get('results', []):
                res = dict(res, requestedAt=payload.get('requestedAt'))
                if aplicar_cotacao(a, res):
                    alterados.add(ticker)
                    log(f'{ticker}: dados disponíveis aceitos', '✅')
                    break
        except HTTPError as exc:
            log(f'{ticker}: HTTP {exc.code}; reserva preservada', '⚠️')
            if exc.code in (401, 429):
                break
        except Exception as exc:
            log(f'{ticker}: {type(exc).__name__}; reserva preservada', '⚠️')
        time.sleep(0.4)
    log(f'{len(alterados)}/{len(acoes)} ativos com dados disponíveis atualizados', '📊')
    return len(alterados)

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
    tickers = tickers or [a["ticker"] for a in data["acoes"]]
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
            log(f"  {ticker}: {type(e).__name__}; dados preservados", "⚠️")
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

    if fund_ok or rec_ok:
        salvar_json(data)
    else:
        log("Nenhum dado validado; arquivo e datas preservados", "⚠️")
        return

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
