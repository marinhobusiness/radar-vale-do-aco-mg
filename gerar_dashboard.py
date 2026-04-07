"""
gerar_dashboard.py — Radar Imobiliário do Vale do Aço
Consome o JSON da análise e gera o index.html atualizado
pronto para publicação no GitHub Pages
Autor: Wederson Marinho · Data Scientist
"""

import json
import sys
from pathlib import Path
from datetime import date

OUTPUT_DIR = Path("dados")
REPO_DIR   = Path(".")   # raiz do repositório — onde fica o index.html


def fmt_brl(valor):
    """Formata número como moeda brasileira sem R$."""
    if valor is None:
        return "—"
    try:
        v = int(valor)
    except (ValueError, TypeError):
        return "—"
    return f"{v:,}".replace(",", ".")


def pct(valor):
    if valor is None:
        return "—"
    return f"{valor:.1f}%"


def gerar_html(payload):
    meta     = payload["meta"]
    resumo   = payload["resumo_mercado"]
    bairros  = payload["bairros"]
    tipols   = payload["tipologias"]
    compos   = payload["composicao_oferta"]
    macro    = meta["fontes_macro"]

    edicao        = meta["edicao"]
    data_coleta   = meta["data_coleta"]
    n_total       = meta["n_total"]
    selic         = macro["selic"]["valor"]
    ipca_12m      = macro["ipca_12m"]["valor"]
    bh_m2         = macro["bh_m2"]["valor"]
    fipezap_2025  = macro["fipezap_2025"]["valor"]
    pm2_mediana   = resumo["pm2_mediana"]

    # Top 10 bairros para as barras
    top_bairros = sorted(bairros, key=lambda x: x["mediana"], reverse=True)[:10]
    max_val = top_bairros[0]["mediana"] if top_bairros else 10000

    # Dados para os gráficos JS
    bairros_js = json.dumps([
        {
            "nome":    b["bairro"],
            "val":     b["mediana"],
            "n":       b["n"],
            "ic_inf":  b.get("ic95_inf"),
            "ic_sup":  b.get("ic95_sup"),
            "cat":     "alto" if b["mediana"] >= 7000 else "medio" if b["mediana"] >= 5000 else "padrao"
        }
        for b in top_bairros
    ], ensure_ascii=False)

    composicao_labels = json.dumps([c["tipo"]  for c in compos], ensure_ascii=False)
    composicao_data   = json.dumps([c["pct"]   for c in compos])

    tipol_labels  = json.dumps([f"{int(t['quartos'])} qto{'s' if t['quartos'] > 1 else ''}" for t in tipols])
    tipol_yields  = json.dumps([t.get("yield_bruto") for t in tipols])
    tipol_pm2     = json.dumps([t["preco_m2_med"] for t in tipols])
    tipol_aluguel = json.dumps([t["aluguel_est"] for t in tipols])

    bh_labels = json.dumps([b["bairro"] for b in top_bairros[:5]], ensure_ascii=False)
    bh_ipatinga = json.dumps([b["mediana"] for b in top_bairros[:5]])

    linhas_tabela = ""
    for b in top_bairros:
        cls = "td-up" if b["mediana"] >= 7000 else "td-md" if b["mediana"] >= 5000 else "td-dn"
        ic  = (
            f"R$ {fmt_brl(b.get('ic95_inf'))} – R$ {fmt_brl(b.get('ic95_sup'))}"
            if b.get("ic95_inf") else "—"
        )
        linhas_tabela += f"""
        <tr>
          <td class="td-k">{b['bairro']}</td>
          <td class="td-m">{b['n']}</td>
          <td class="{cls} td-m">R$ {fmt_brl(b['mediana'])}</td>
          <td class="td-m">R$ {fmt_brl(b['media'])}</td>
          <td class="td-m">R$ {fmt_brl(b['dp'])}</td>
          <td class="td-s">{ic}</td>
          <td class="td-m">{pct(b.get('desconto_bh_pct'))}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Radar Imobiliário do Vale do Aço — Análise quantitativa do mercado de Ipatinga-MG. {edicao}. Dados reais de {n_total} anúncios verificados. Por Wederson Marinho, Data Scientist.">
<meta name="author" content="Wederson Marinho">
<title>Radar Imobiliário · Vale do Aço · {edicao}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{{--ink:#0D1B2A;--navy:#1B3A5C;--steel:#2E6DA4;--gold:#C9A84C;--gold-lt:#E8C97A;--bg:#F0F4F8;--card:#FFFFFF;--muted:#718096;--border:#E2E8F0;--green:#276749;}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'IBM Plex Sans',sans-serif;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.6;}}
header{{background:var(--ink);border-bottom:3px solid var(--gold);position:sticky;top:0;z-index:200;box-shadow:0 4px 20px rgba(0,0,0,.35);}}
.hdr{{max-width:1360px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;padding:13px 28px;gap:16px;flex-wrap:wrap;}}
.brand-name{{font-family:'Cormorant Garamond',serif;font-size:1.4rem;font-weight:700;color:var(--gold);}}
.brand-sub{{font-size:.68rem;color:rgba(255,255,255,.4);letter-spacing:.08em;text-transform:uppercase;}}
.badge{{background:var(--steel);color:#fff;font-size:.67rem;font-weight:600;padding:4px 12px;border-radius:20px;letter-spacing:.07em;text-transform:uppercase;}}
.badge-n{{border:1px solid var(--green);color:#4CAF7D;font-size:.67rem;padding:4px 12px;border-radius:20px;font-family:'IBM Plex Mono',monospace;}}
.badge-out{{border:1px solid var(--gold);color:var(--gold-lt);font-size:.67rem;padding:4px 12px;border-radius:20px;}}
.analyst-name{{font-size:.82rem;font-weight:600;color:#fff;text-align:right;}}
.analyst-cred{{font-size:.67rem;color:rgba(255,255,255,.4);text-align:right;}}
.kpi-strip{{background:var(--navy);border-bottom:2px solid rgba(201,168,76,.25);display:grid;grid-template-columns:repeat(5,1fr);}}
.kpi{{padding:15px 18px;border-right:1px solid rgba(255,255,255,.07);}}
.kpi:last-child{{border-right:none;}}
.kpi:hover{{background:rgba(201,168,76,.08);}}
.kpi-lbl{{font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.4);margin-bottom:4px;}}
.kpi-val{{font-family:'Cormorant Garamond',serif;font-size:1.85rem;font-weight:700;color:var(--gold);line-height:1;}}
.kpi-chg{{font-size:.71rem;font-weight:600;margin-top:3px;font-family:'IBM Plex Mono',monospace;}}
.kpi-src{{font-size:.61rem;color:rgba(255,255,255,.28);margin-top:2px;}}
.up{{color:#4CAF7D;}}.dn{{color:#E57373;}}.nt{{color:rgba(255,255,255,.5);}}
.main{{max-width:1360px;margin:0 auto;padding:26px 24px;display:flex;flex-direction:column;gap:22px;}}
.sec-lbl{{font-size:.64rem;letter-spacing:.16em;text-transform:uppercase;font-weight:600;color:var(--gold);display:flex;align-items:center;gap:12px;margin-bottom:-6px;}}
.sec-lbl::after{{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--gold),transparent);opacity:.25;}}
.row{{display:grid;gap:20px;}}.c2{{grid-template-columns:1fr 1fr;}}.c53{{grid-template-columns:5fr 3fr;}}
.card{{background:var(--card);border-radius:10px;border-top:3px solid transparent;box-shadow:0 1px 8px rgba(13,27,42,.07);padding:22px 24px;transition:transform .18s,box-shadow .18s;}}
.card:hover{{transform:translateY(-2px);box-shadow:0 6px 22px rgba(13,27,42,.12);}}
.c-gold{{border-top-color:var(--gold);}}.c-blue{{border-top-color:var(--steel);}}.c-navy{{border-top-color:var(--navy);background:var(--ink);}}.c-green{{border-top-color:var(--green);}}
.card-title{{font-family:'Cormorant Garamond',serif;font-size:1.05rem;font-weight:700;color:var(--ink);}}
.c-navy .card-title{{color:var(--gold);}}.card-sub{{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-top:2px;}}
.c-navy .card-sub{{color:rgba(255,255,255,.32);}}.card-rule{{height:1px;background:linear-gradient(90deg,var(--gold),transparent);opacity:.3;margin:12px 0 16px;}}
.ch{{position:relative;height:280px;}}.ch-lg{{position:relative;height:340px;}}
.bairros{{display:flex;flex-direction:column;gap:9px;}}
.b-row{{display:flex;align-items:center;gap:10px;}}
.b-nome{{min-width:165px;font-size:.8rem;color:var(--ink);font-weight:500;}}
.b-track{{flex:1;background:#EEF2F7;border-radius:4px;height:10px;overflow:hidden;}}
.b-fill{{height:100%;border-radius:4px;transition:width .9s cubic-bezier(.4,0,.2,1);}}
.b-val{{min-width:105px;text-align:right;font-family:'IBM Plex Mono',monospace;font-size:.77rem;color:var(--muted);}}
.dt{{width:100%;border-collapse:collapse;font-size:.8rem;}}
.dt th{{background:var(--ink);color:var(--gold);padding:8px 12px;text-align:left;font-size:.64rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;}}
.dt td{{padding:8px 12px;border-bottom:1px solid var(--border);}}
.dt tr:nth-child(even) td{{background:#F8FAFC;}}.dt tr:hover td{{background:#EDF2FF;}}
.td-k{{font-weight:600;}}.td-up{{color:var(--green);font-weight:600;font-family:'IBM Plex Mono',monospace;}}
.td-md{{color:#B7791F;font-weight:600;font-family:'IBM Plex Mono',monospace;}}
.td-dn{{color:#9B2226;font-weight:600;font-family:'IBM Plex Mono',monospace;}}
.td-m{{font-family:'IBM Plex Mono',monospace;}}.td-s{{font-size:.69rem;color:var(--muted);}}
.y-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px;}}
.y-item{{background:var(--bg);border-radius:8px;padding:12px;text-align:center;}}
.y-type{{font-size:.64rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);}}
.y-num{{font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:700;color:var(--steel);margin:4px 0;}}
.y-sub{{font-size:.67rem;color:#A0AEC0;}}
.macro-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}}
.m-item{{background:var(--card);border-radius:8px;padding:14px;border-left:3px solid var(--steel);box-shadow:0 1px 6px rgba(13,27,42,.06);}}
.m-val{{font-family:'Cormorant Garamond',serif;font-size:1.5rem;font-weight:700;color:var(--ink);}}
.m-lbl{{font-size:.72rem;color:var(--muted);margin-top:2px;}}.m-src{{font-size:.63rem;color:#A0AEC0;margin-top:4px;}}
.nota-metodo{{background:#FFFBEB;border:1px solid var(--gold);border-radius:8px;padding:14px 16px;font-size:.78rem;line-height:1.6;color:var(--ink);}}
.nota-metodo strong{{color:var(--navy);}}
.persp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
.p-item{{display:flex;gap:12px;align-items:flex-start;}}
.p-icon{{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;}}
.p-body{{font-size:.82rem;line-height:1.6;color:#4A5568;}}
.p-body strong{{display:block;color:var(--ink);font-size:.84rem;margin-bottom:2px;}}
.f-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}}
.f-item{{background:var(--bg);border-radius:6px;padding:10px 12px;}}
.f-nome{{font-size:.73rem;font-weight:600;color:var(--navy);}}.f-desc{{font-size:.67rem;color:var(--muted);margin-top:2px;line-height:1.4;}}
.note{{font-size:.71rem;color:var(--muted);margin-top:10px;line-height:1.5;}}
.note em{{font-style:normal;color:var(--gold);font-weight:500;}}
.note-dk{{font-size:.71rem;color:rgba(255,255,255,.3);margin-top:10px;line-height:1.5;}}
footer{{background:var(--ink);border-top:3px solid var(--gold);padding:22px 28px;}}
.ftr{{max-width:1360px;margin:0 auto;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;}}
.f-brand{{font-family:'Cormorant Garamond',serif;font-size:1.1rem;color:var(--gold);font-weight:700;}}
.f-creds{{font-size:.71rem;color:rgba(255,255,255,.42);line-height:1.8;margin-top:4px;}}
.f-creds a{{color:var(--gold-lt);text-decoration:none;}}
.f-orcid{{font-family:'IBM Plex Mono',monospace;font-size:.67rem;color:rgba(255,255,255,.28);margin-top:4px;}}
.f-notice{{font-size:.67rem;color:rgba(255,255,255,.28);max-width:420px;line-height:1.55;}}
@media(max-width:1024px){{.kpi-strip{{grid-template-columns:repeat(3,1fr);}}.c53,.c2{{grid-template-columns:1fr;}}.macro-grid,.persp-grid,.f-grid{{grid-template-columns:1fr 1fr;}}}}
@media(max-width:640px){{.kpi-strip{{grid-template-columns:repeat(2,1fr);}}.macro-grid,.persp-grid{{grid-template-columns:1fr;}}.hdr{{flex-direction:column;align-items:flex-start;}}}}
</style>
</head>
<body>

<header>
  <div class="hdr">
    <div>
      <div class="brand-name">Radar Imobiliário · Vale do Aço</div>
      <div class="brand-sub">Ipatinga · Coronel Fabriciano · Timóteo · MG</div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <span class="badge">{edicao}</span>
      <span class="badge-n">n = {n_total} anúncios</span>
      <span class="badge-out">Dados reais verificados</span>
    </div>
    <div>
      <div class="analyst-name">Wederson Marinho</div>
      <div class="analyst-cred">Data Scientist · CRECI-MG 58.263-F · CNAI 51.239</div>
    </div>
  </div>
</header>

<div class="kpi-strip">
  <div class="kpi">
    <div class="kpi-lbl">Preço mediano m² — Ipatinga</div>
    <div class="kpi-val">R$ {fmt_brl(pm2_mediana)}</div>
    <div class="kpi-chg nt">n = {n_total} anúncios · {edicao}</div>
    <div class="kpi-src">Zap / VivaReal / OLX · {data_coleta}</div>
  </div>
  <div class="kpi">
    <div class="kpi-lbl">FipeZAP acumulado 2025</div>
    <div class="kpi-val">+{fipezap_2025}%</div>
    <div class="kpi-chg up">▲ +2,0 p.p. acima do IPCA</div>
    <div class="kpi-src">ANOREG / DataZap · jan/2026</div>
  </div>
  <div class="kpi">
    <div class="kpi-lbl">PIB per capita · Ipatinga</div>
    <div class="kpi-val">R$ 74k</div>
    <div class="kpi-chg up">4º interior de MG</div>
    <div class="kpi-src">IBGE · 2023</div>
  </div>
  <div class="kpi">
    <div class="kpi-lbl">IPCA acumulado 12 meses</div>
    <div class="kpi-val">{ipca_12m}%</div>
    <div class="kpi-chg up">▼ abaixo de 4% pela 1ª vez</div>
    <div class="kpi-src">IBGE · fev/2026 (divulg. 12/mar)</div>
  </div>
  <div class="kpi">
    <div class="kpi-lbl">Selic · Copom mar/2026</div>
    <div class="kpi-val">{selic}%</div>
    <div class="kpi-chg dn">▼ 1º corte em ~2 anos</div>
    <div class="kpi-src">Banco Central · mar/2026</div>
  </div>
</div>

<div class="main">

  <div class="nota-metodo">
    <strong>Nota metodológica:</strong> Este relatório baseia-se em {n_total} anúncios ativos
    coletados nos portais Zap Imóveis, VivaReal e OLX em {data_coleta}.
    O preço por m² é calculado sobre a área privativa declarada no anúncio, com remoção de
    outliers pelo método IQR 1,5×. Outliers extremos (preço/m² fora do intervalo
    [Q1 − 1,5×IQR ; Q3 + 1,5×IQR]) foram excluídos. Bairros com menos de 3 observações
    não integram a análise estatística. <em>Não representa preço de transação efetivada —
    metodologia equivalente ao Índice FipeZAP.</em>
  </div>

  <div class="sec-lbl">Contexto macroeconômico — fontes primárias verificáveis</div>
  <div class="macro-grid">
    <div class="m-item" style="border-left-color:var(--gold);">
      <div class="m-val">235.311</div>
      <div class="m-lbl">População estimada · Ipatinga</div>
      <div class="m-src">IBGE estimativa 2025 · 11º município MG</div>
    </div>
    <div class="m-item">
      <div class="m-val">R$ {fmt_brl(bh_m2)}</div>
      <div class="m-lbl">Preço médio m² · Belo Horizonte</div>
      <div class="m-src">FipeZAP · dez/2025 · valoriz. +12,03% em 12m</div>
    </div>
    <div class="m-item" style="border-left-color:var(--gold);">
      <div class="m-val">1.443</div>
      <div class="m-lbl">Novas empresas abertas</div>
      <div class="m-src">Caravela.info · até nov/2025</div>
    </div>
    <div class="m-item">
      <div class="m-val">78,4 mil</div>
      <div class="m-lbl">Empregos com carteira assinada</div>
      <div class="m-src">Caravela.info · nov/2025 · renda média R$ 2.600</div>
    </div>
  </div>

  <div class="sec-lbl">Preços por m² — {n_total} anúncios coletados e analisados</div>
  <div class="row c53">
    <div class="card c-gold">
      <div class="card-title">Preço mediano por m² — por bairro</div>
      <div class="card-sub">Mediana · n por bairro declarado · {data_coleta} · Zap / VivaReal / OLX</div>
      <div class="card-rule"></div>
      <div class="bairros" id="bairros-container"></div>
      <p class="note" style="margin-top:12px;">
        Barras representam a mediana. IC 95% exibido na tabela abaixo.
        <em>Bairros com n &lt; 3 excluídos.</em>
      </p>
    </div>
    <div class="card c-blue">
      <div class="card-title">Composição da oferta ativa</div>
      <div class="card-sub">Distribuição por tipo · {edicao}</div>
      <div class="card-rule"></div>
      <div class="ch">
        <canvas id="pizzaChart"></canvas>
      </div>
      <p class="note" style="margin-top:10px;">
        Fonte: Zap / VivaReal / OLX · n = {n_total} anúncios únicos após deduplicação.
      </p>
    </div>
  </div>

  <div class="card c-navy">
    <div class="card-title">Tabela estatística completa — por bairro</div>
    <div class="card-sub">Mediana · Média · Desvio padrão · IC 95% · Desconto vs. BH · {data_coleta}</div>
    <div class="card-rule"></div>
    <table class="dt">
      <thead>
        <tr>
          <th>Bairro</th><th>n</th><th>Mediana m²</th>
          <th>Média m²</th><th>Desvio p.</th>
          <th>IC 95%</th><th>Desc. vs BH</th>
        </tr>
      </thead>
      <tbody>
        {linhas_tabela}
      </tbody>
    </table>
    <p class="note-dk" style="margin-top:12px;">
      IC 95% calculado via distribuição t de Student. Desconto vs. BH calculado sobre mediana Ipatinga
      vs. FipeZAP BH dez/2025 (R$ {fmt_brl(bh_m2)}/m²).
    </p>
  </div>

  <div class="sec-lbl">Rentabilidade e análise comparativa</div>
  <div class="row c2">
    <div class="card c-green">
      <div class="card-title">Yield bruto estimado por tipologia</div>
      <div class="card-sub">Cap rate anual estimado · {edicao}</div>
      <div class="card-rule"></div>
      <div class="ch-lg">
        <canvas id="yieldChart"></canvas>
      </div>
      <div class="y-grid">
        <div class="y-item">
          <div class="y-type">Selic · mar/2026</div>
          <div class="y-num">{selic}%</div>
          <div class="y-sub">Banco Central</div>
        </div>
        <div class="y-item">
          <div class="y-type">IPCA 12 meses</div>
          <div class="y-num">{ipca_12m}%</div>
          <div class="y-sub">IBGE · fev/2026</div>
        </div>
      </div>
      <p class="note" style="margin-top:10px;">
        Yield estimado: aluguel mediano anualizado ÷ valor mediano de compra.
        <em>Aluguel estimado como 0,42% do valor de venda (referência FipeZAP Locação histórico).</em>
      </p>
    </div>
    <div class="card c-gold">
      <div class="card-title">Desconto vs. Belo Horizonte — top 5 bairros</div>
      <div class="card-sub">Mediana Ipatinga vs. FipeZAP BH R$ {fmt_brl(bh_m2)}/m² · dez/2025</div>
      <div class="card-rule"></div>
      <div class="ch-lg">
        <canvas id="bhChart"></canvas>
      </div>
      <p class="note" style="margin-top:10px;">
        Ipatinga opera estruturalmente abaixo de BH. O spread tende a convergir
        com urbanização regional e melhora de infraestrutura.
      </p>
    </div>
  </div>

  <div class="sec-lbl">Perspectivas — próximo trimestre</div>
  <div class="card c-gold">
    <div class="card-title">Análise de cenário — dados públicos verificáveis</div>
    <div class="card-sub">Mercado imobiliário de Ipatinga · {edicao}</div>
    <div class="card-rule"></div>
    <div class="persp-grid">
      <div class="p-item">
        <div class="p-icon" style="background:#EBF5FB;">📈</div>
        <div class="p-body">
          <strong>Demanda estrutural sustentada</strong>
          Ipatinga concentra fluxo migratório do Colar Metropolitano (778 mil hab.). Com 1.443 empresas abertas até nov/2025 e expansão de serviços, a demanda de médio padrão é resiliente a oscilações de curto prazo.
        </div>
      </div>
      <div class="p-item">
        <div class="p-icon" style="background:#EDF7F0;">🏗️</div>
        <div class="p-body">
          <strong>Oportunidade: comercial de pequeno porte</strong>
          Expansão de saúde, educação e tecnologia eleva procura por salas de 40–80 m². Yield estimado acima de 7% a.a. posiciona o segmento como alternativa competitiva à renda fixa para pessoa física.
        </div>
      </div>
      <div class="p-item">
        <div class="p-icon" style="background:#FFF5F5;">⚠️</div>
        <div class="p-body">
          <strong>Risco: crédito imobiliário comprimido</strong>
          Selic em {selic}% (Bacen mar/2026) encarece o financiamento. Possíveis mudanças no FGTS para imóveis acima de R$ 350 mil devem ser monitoradas no próximo semestre.
        </div>
      </div>
      <div class="p-item">
        <div class="p-icon" style="background:#FEFCE8;">💡</div>
        <div class="p-body">
          <strong>Desconto vs. BH — oportunidade de longo prazo</strong>
          Spread estrutural frente à capital tende a convergir com urbanização. Investidor com horizonte 5+ anos captura valorização real e yield simultaneamente.
        </div>
      </div>
    </div>
  </div>

  <div class="sec-lbl">Fontes e metodologia</div>
  <div class="card c-blue">
    <div class="card-title">Todos os dados são verificáveis e públicos · n = {n_total} observações</div>
    <div class="card-sub">Metodologia equivalente ao Índice FipeZAP para dados de oferta ativa</div>
    <div class="card-rule"></div>
    <div class="f-grid">
      <div class="f-item"><div class="f-nome">IBGE Cidades</div><div class="f-desc">População 2025, PIB per capita 2023. ibge.gov.br</div></div>
      <div class="f-item"><div class="f-nome">FipeZAP / DataZap</div><div class="f-desc">Acumulados 2024 (+{fipezap_2025}%) e 2025. BH R$ {fmt_brl(bh_m2)}/m² dez/2025. datazap.com.br</div></div>
      <div class="f-item"><div class="f-nome">ANOREG/BR</div><div class="f-desc">Análise FipeZAP 2025. anoreg.org.br · jan/2026</div></div>
      <div class="f-item"><div class="f-nome">Banco Central do Brasil</div><div class="f-desc">Selic {selic}% · Copom mar/2026. bcb.gov.br</div></div>
      <div class="f-item"><div class="f-nome">IBGE / IPCA</div><div class="f-desc">Acumulado 12m: {ipca_12m}% (fev/2026, divulg. 12/mar/2026). ibge.gov.br</div></div>
      <div class="f-item"><div class="f-nome">Zap / VivaReal / OLX</div><div class="f-desc">Anúncios ativos coletados em {data_coleta}. n = {n_total}. Grupo OLX Brasil.</div></div>
    </div>
    <p class="note" style="margin-top:14px;">
      Este relatório <em>não constitui recomendação de investimento</em>.
      Para laudo formal (PTAM · ABNT NBR 14653), consulte profissional habilitado CRECI/CNAI.
      Análise: Wederson Marinho · CRECI-MG 58.263-F · CNAI 51.239 · Data Scientist.
    </p>
  </div>

</div>

<footer>
  <div class="ftr">
    <div>
      <div class="f-brand">Radar Imobiliário · Vale do Aço</div>
      <div class="f-creds">
        Wederson Marinho · Data Scientist<br>
        CRECI-MG 58.263-F · CNAI 51.239<br>
        <a href="mailto:marinhobusiness@gmail.com">marinhobusiness@gmail.com</a> ·
        <a href="https://linkedin.com/in/marinhobusiness" target="_blank">linkedin.com/in/marinhobusiness</a>
      </div>
      <div class="f-orcid">ORCID: 0009-0004-6401-3465</div>
    </div>
    <div class="f-notice">
      Publicação trimestral gratuita. Dados coletados de fontes públicas.
      Livre reprodução com atribuição ao autor. Não constitui recomendação de investimento.
      n = {n_total} anúncios únicos · coleta: {data_coleta}.
    </div>
  </div>
</footer>

<script>
var INK='#0D1B2A',NAVY='#1B3A5C',STEEL='#2E6DA4',GOLD='#C9A84C',MUTED='#4A5568',BG='#F0F4F8',GREEN='#276749';
var CAT_COR={{alto:STEEL,medio:GOLD,padrao:NAVY}};

// BAIRROS
var bairros={bairros_js};
var MAX_VAL=Math.max.apply(null,bairros.map(function(b){{return b.val;}})) * 1.1;
var cont=document.getElementById('bairros-container');
for(var i=0;i<bairros.length;i++){{
  var b=bairros[i];
  var pct=(b.val/MAX_VAL*100).toFixed(1);
  var fmt='R$ '+b.val.toLocaleString('pt-BR')+'/m\u00b2 (n='+b.n+')';
  var div=document.createElement('div');
  div.className='b-row';
  div.innerHTML='<div class="b-nome">'+b.nome+'</div><div class="b-track"><div class="b-fill" style="width:0%;background:'+CAT_COR[b.cat]+';" data-w="'+pct+'"></div></div><div class="b-val">'+fmt+'</div>';
  cont.appendChild(div);
}}
setTimeout(function(){{
  document.querySelectorAll('.b-fill').forEach(function(el){{el.style.width=el.dataset.w+'%';}});
}},150);

// PIZZA
var compLabels={composicao_labels};
var compData={composicao_data};
new Chart(document.getElementById('pizzaChart'),{{
  type:'doughnut',
  data:{{labels:compLabels,datasets:[{{data:compData,backgroundColor:[STEEL,NAVY,GOLD,'#4A9E6B','#7B6FBA'],borderColor:'#fff',borderWidth:2,hoverOffset:8}}]}},
  options:{{responsive:true,maintainAspectRatio:false,cutout:'60%',plugins:{{
    legend:{{position:'bottom',labels:{{font:{{size:11}},color:MUTED,padding:12}}}},
    tooltip:{{callbacks:{{label:function(ctx){{return ' '+ctx.label+': '+ctx.parsed+'%';}}}}}}
  }}}}
}});

// YIELD
var tipLabels={tipol_labels};
var tipYield={tipol_yields};
new Chart(document.getElementById('yieldChart'),{{
  type:'bar',
  data:{{labels:tipLabels,datasets:[{{
    label:'Yield bruto estimado a.a. (%)',data:tipYield,
    backgroundColor:tipYield.map(function(v,i){{return i===tipYield.length-1?'rgba(201,168,76,0.85)':'rgba(46,109,164,'+(0.55+i*0.1)+')';}}) ,
    borderRadius:5,borderSkipped:false
  }}]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:function(ctx){{return ' '+ctx.parsed.y+'% a.a. estimado';}}}}}}}}
    ,scales:{{x:{{ticks:{{color:MUTED,font:{{size:10}}}},grid:{{display:false}}}},y:{{ticks:{{color:MUTED,font:{{size:10}},callback:function(v){{return v+'%';}}}},grid:{{color:BG}},min:3,max:9}}}}
  }}
}});

// BH
var bhLabels={bh_labels};
var bhIpatinga={bh_ipatinga};
var bhVal={bh_m2};
new Chart(document.getElementById('bhChart'),{{
  type:'bar',
  data:{{labels:bhLabels,datasets:[
    {{label:'Ipatinga \u2014 mediana',data:bhIpatinga,backgroundColor:STEEL,borderRadius:4}},
    {{label:'BH \u2014 FipeZAP dez/2025',data:bhLabels.map(function(){{return bhVal;}}),backgroundColor:'rgba(201,168,76,0.25)',borderWidth:2,borderColor:GOLD,borderRadius:4}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{font:{{size:10}},color:MUTED,padding:10}}}},
      tooltip:{{callbacks:{{label:function(ctx){{
        if(ctx.datasetIndex===1)return ' BH: R$ '+bhVal.toLocaleString('pt-BR')+'/m\u00b2';
        var d=((1-ctx.parsed.y/bhVal)*100).toFixed(0);
        return ' R$ '+ctx.parsed.y.toLocaleString('pt-BR')+'/m\u00b2 ('+d+'% abaixo de BH)';
      }}}}}}
    }},
    scales:{{x:{{ticks:{{color:MUTED,font:{{size:9.5}}}},grid:{{display:false}}}},
      y:{{ticks:{{color:MUTED,font:{{size:9.5}},callback:function(v){{return 'R$'+v.toLocaleString('pt-BR');}}}},grid:{{color:BG}},min:0}}}}
  }}
}});
</script>
</body>
</html>"""

    return html


def gerar(caminho_json, caminho_saida=None):
    print("=" * 60)
    print("GERAÇÃO DO DASHBOARD — RADAR IMOBILIÁRIO VALE DO AÇO")
    print("=" * 60)

    with open(caminho_json, "r", encoding="utf-8") as f:
        payload = json.load(f)

    html = gerar_html(payload)

    if not caminho_saida:
        caminho_saida = REPO_DIR / "index.html"

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(html)

    kb = len(html.encode("utf-8")) / 1024
    print(f"\n✅ Dashboard gerado: {caminho_saida} ({kb:.1f} KB)")
    print(f"   Edição: {payload['meta']['edicao']}")
    print(f"   Observações: {payload['meta']['n_total']}")
    return caminho_saida


if __name__ == "__main__":
    if len(sys.argv) < 2:
        jsons = sorted(Path("dados").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not jsons:
            print("❌ Nenhum JSON encontrado em dados/. Execute analisar.py primeiro.")
            sys.exit(1)
        caminho = str(jsons[0])
        print(f"ℹ️  Usando JSON mais recente: {caminho}")
    else:
        caminho = sys.argv[1]

    saida = gerar(caminho)
    print(f"\nPróximo passo: python publicar.py")
