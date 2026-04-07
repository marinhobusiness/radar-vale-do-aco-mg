"""
analisar.py — Radar Imobiliário do Vale do Aço
Análise estatística robusta dos dados coletados
Produz: estatísticas por bairro, gráficos, JSON para o dashboard
Autor: Wederson Marinho · Data Scientist
"""

import pandas as pd
import numpy as np
import json
import sys
import warnings
from pathlib import Path
from datetime import date
from scipy import stats

warnings.filterwarnings("ignore")

OUTPUT_DIR = Path("dados")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
N_MIN_BAIRRO = 3   # mínimo de observações para calcular estatísticas de bairro
IPCA_12M     = 3.81  # IBGE fev/2026 — atualizar a cada edição
SELIC        = 14.75  # Bacen mar/2026
BH_M2        = 10642  # FipeZAP dez/2025
FIPEZAP_2025 = 6.52
FIPEZAP_2024 = 7.73
DATA_REF     = date.today().isoformat()


# ── CARGA E LIMPEZA ───────────────────────────────────────────────────────────
def carregar(caminho_csv):
    """Carrega e limpa o CSV de dados coletados."""
    df = pd.read_csv(caminho_csv, encoding="utf-8")
    print(f"📂 Carregado: {len(df)} registros de {caminho_csv}")

    # Converter tipos
    df["area_m2"]          = pd.to_numeric(df["area_m2"], errors="coerce")
    df["valor_anunciado"]  = pd.to_numeric(df["valor_anunciado"], errors="coerce")
    df["preco_m2"]         = pd.to_numeric(df["preco_m2"], errors="coerce")
    df["quartos"]          = pd.to_numeric(df["quartos"], errors="coerce")
    df["data_coleta"]      = pd.to_datetime(df["data_coleta"], errors="coerce")

    # Remover outliers extremos (IQR 1.5x)
    Q1 = df["preco_m2"].quantile(0.25)
    Q3 = df["preco_m2"].quantile(0.75)
    IQR = Q3 - Q1
    antes = len(df)
    df = df[
        (df["preco_m2"] >= Q1 - 1.5 * IQR) &
        (df["preco_m2"] <= Q3 + 1.5 * IQR) &
        (df["area_m2"].between(20, 500)) &
        (df["valor_anunciado"].between(100_000, 10_000_000))
    ]
    print(f"🧹 Outliers removidos: {antes - len(df)} | Amostra final: {len(df)}")
    return df


# ── ESTATÍSTICAS POR BAIRRO ───────────────────────────────────────────────────
def estatisticas_bairro(df):
    """
    Calcula estatísticas completas por bairro.
    Retorna apenas bairros com n >= N_MIN_BAIRRO.
    """
    grupos = df.groupby("bairro")["preco_m2"]

    stats_bairro = []
    for bairro, serie in grupos:
        n = len(serie)
        if n < N_MIN_BAIRRO:
            continue

        media   = serie.mean()
        mediana = serie.median()
        dp      = serie.std()
        q1      = serie.quantile(0.25)
        q3      = serie.quantile(0.75)

        # Intervalo de confiança 95% (t-distribution)
        if n >= 5:
            ic = stats.t.interval(0.95, df=n - 1, loc=media, scale=stats.sem(serie))
        else:
            ic = (None, None)

        stats_bairro.append({
            "bairro":   bairro,
            "n":        n,
            "media":    round(media),
            "mediana":  round(mediana),
            "dp":       round(dp),
            "q1":       round(q1),
            "q3":       round(q3),
            "min":      round(serie.min()),
            "max":      round(serie.max()),
            "ic95_inf": round(ic[0]) if ic[0] else None,
            "ic95_sup": round(ic[1]) if ic[1] else None,
            "desconto_bh_pct": round((1 - mediana / BH_M2) * 100, 1),
        })

    df_stats = pd.DataFrame(stats_bairro).sort_values("mediana", ascending=False)
    print(f"\n📊 Bairros analisados: {len(df_stats)} (com n ≥ {N_MIN_BAIRRO})")
    return df_stats


# ── ESTATÍSTICAS POR TIPOLOGIA ────────────────────────────────────────────────
def estatisticas_tipologia(df):
    """Preço médio e mediano por número de quartos."""
    df_q = df[df["quartos"].notna() & df["quartos"].between(1, 5)]
    grupos = df_q.groupby("quartos")

    tipologias = []
    for q, grupo in grupos:
        n = len(grupo)
        if n < N_MIN_BAIRRO:
            continue

        pm2_med    = grupo["preco_m2"].median()
        valor_med  = grupo["valor_anunciado"].median()
        area_med   = grupo["area_m2"].median()

        # Yield estimado (usando aluguel estimado como ~0,42% do valor)
        # Referência: FipeZAP locação divide yield médio histórico
        aluguel_est = valor_med * 0.0042
        yield_bruto = (aluguel_est * 12 / valor_med * 100) if valor_med else None

        tipologias.append({
            "quartos":       int(q),
            "n":             n,
            "preco_m2_med":  round(pm2_med),
            "valor_med":     round(valor_med),
            "area_med":      round(area_med, 1),
            "aluguel_est":   round(aluguel_est),
            "yield_bruto":   round(yield_bruto, 2) if yield_bruto else None,
        })

    return pd.DataFrame(tipologias)


# ── ANÁLISE POR PORTAL ────────────────────────────────────────────────────────
def analise_portal(df):
    """Distribuição e comparação entre portais."""
    return df.groupby("portal").agg(
        n=("preco_m2", "count"),
        preco_m2_medio=("preco_m2", "mean"),
        preco_m2_mediano=("preco_m2", "median"),
    ).round(0).reset_index()


# ── COMPOSIÇÃO DA OFERTA ──────────────────────────────────────────────────────
def composicao_oferta(df):
    """Distribuição por tipo de imóvel."""
    mapa_tipo = {
        "APARTMENT": "Apartamento",
        "HOME": "Casa",
        "COMMERCIAL": "Comercial",
        "LAND": "Terreno",
        "PENTHOUSE": "Cobertura",
    }
    df = df.copy()
    df["tipo_pt"] = df["tipo"].map(mapa_tipo).fillna("Outro")
    contagem = df["tipo_pt"].value_counts()
    pct = (contagem / contagem.sum() * 100).round(1)
    return pd.DataFrame({"tipo": contagem.index, "n": contagem.values, "pct": pct.values})


# ── GRÁFICOS ──────────────────────────────────────────────────────────────────
def gerar_graficos(df, df_bairros, df_tipologia):
    """
    Gera todos os gráficos e salva em dados/graficos/
    Retorna dicionário com caminhos dos arquivos.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    GRAFICO_DIR = OUTPUT_DIR / "graficos"
    GRAFICO_DIR.mkdir(exist_ok=True)

    # Paleta
    AZUL   = "#2E6DA4"
    DOURADO = "#C9A84C"
    NAVY   = "#1B3A5C"
    VERDE  = "#2D6A4F"
    CINZA  = "#4A5568"
    BG     = "#F4F6F9"

    arquivos = {}

    # ── 1. Preço por bairro (barras horizontais com IC95) ────────────────────
    fig, ax = plt.subplots(figsize=(10, max(6, len(df_bairros) * 0.55)))
    fig.patch.set_facecolor("none")
    ax.set_facecolor(BG)

    top = df_bairros.head(12).iloc[::-1]
    cores = [AZUL if m >= 7000 else DOURADO if m >= 5000 else NAVY for m in top["mediana"]]
    bars = ax.barh(top["bairro"], top["mediana"], color=cores, height=0.65, edgecolor="white", lw=0.5)

    # Barras de erro (IC 95%)
    erros_inf = top["mediana"] - top["ic95_inf"].fillna(top["mediana"])
    erros_sup = top["ic95_sup"].fillna(top["mediana"]) - top["mediana"]
    ax.errorbar(
        top["mediana"], top["bairro"],
        xerr=[erros_inf, erros_sup],
        fmt="none", color="#718096", capsize=4, lw=1.2, alpha=0.7
    )

    # Rótulos com n
    for bar, (_, row) in zip(bars, top.iterrows()):
        ax.text(
            bar.get_width() + 100, bar.get_y() + bar.get_height() / 2,
            f"R$ {row['mediana']:,.0f}  (n={row['n']})".replace(",", "."),
            va="center", ha="left", fontsize=8, color="#0D1B2A", fontweight="bold"
        )

    ax.set_xlabel("Preço mediano por m² (R$)", fontsize=9, color=CINZA)
    ax.set_xlim(0, df_bairros["mediana"].max() * 1.35)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.spines["left"].set_color("#E2E8F0")
    ax.tick_params(colors=CINZA, labelsize=9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}".replace(",", ".")))
    ax.grid(axis="x", alpha=0.35, linestyle="--", color="#CBD5E0")
    ax.set_title(
        f"Preço mediano por m² — Ipatinga-MG | {DATA_REF}\n"
        f"Barras de erro = IC 95% | Fonte: Zap / VivaReal / OLX",
        fontsize=9.5, color="#0D1B2A", fontweight="bold", pad=10
    )
    legenda = [
        mpatches.Patch(color=AZUL,   label="Alto padrão (>R$ 7.000/m²)"),
        mpatches.Patch(color=DOURADO, label="Médio-alto (R$ 5.000–7.000/m²)"),
        mpatches.Patch(color=NAVY,   label="Popular/médio (<R$ 5.000/m²)"),
    ]
    ax.legend(handles=legenda, loc="lower right", fontsize=8.5, framealpha=0.85)

    plt.tight_layout()
    p1 = str(GRAFICO_DIR / "01_preco_bairro.png")
    fig.savefig(p1, dpi=180, bbox_inches="tight", facecolor="none")
    plt.close()
    arquivos["preco_bairro"] = p1
    print(f"  ✓ Gráfico 1: {p1}")

    # ── 2. Distribuição dos preços (histograma + KDE) ─────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("none")
    ax.set_facecolor(BG)

    pm2 = df["preco_m2"].dropna()
    ax.hist(pm2, bins=40, color=AZUL, alpha=0.65, edgecolor="white", lw=0.3, density=True)

    # KDE manual
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(pm2, bw_method="scott")
    x_kde = np.linspace(pm2.min(), pm2.max(), 300)
    ax.plot(x_kde, kde(x_kde), color=DOURADO, lw=2.5, label="KDE")

    # Mediana e média
    ax.axvline(pm2.median(), color=VERDE, lw=2, linestyle="--", label=f"Mediana: R$ {pm2.median():,.0f}".replace(",", "."))
    ax.axvline(pm2.mean(),   color="#9B2226", lw=2, linestyle=":",  label=f"Média: R$ {pm2.mean():,.0f}".replace(",", "."))

    ax.set_xlabel("Preço por m² (R$)", fontsize=9, color=CINZA)
    ax.set_ylabel("Densidade", fontsize=9, color=CINZA)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=CINZA, labelsize=9)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}".replace(",", ".")))
    ax.legend(fontsize=9, framealpha=0.85)
    ax.set_title(
        f"Distribuição dos preços por m² — Ipatinga-MG | n={len(pm2)} anúncios | {DATA_REF}",
        fontsize=9.5, color="#0D1B2A", fontweight="bold", pad=10
    )
    plt.tight_layout()
    p2 = str(GRAFICO_DIR / "02_distribuicao.png")
    fig.savefig(p2, dpi=180, bbox_inches="tight", facecolor="none")
    plt.close()
    arquivos["distribuicao"] = p2
    print(f"  ✓ Gráfico 2: {p2}")

    # ── 3. Boxplot por número de quartos ─────────────────────────────────────
    df_q = df[df["quartos"].between(1, 4)].copy()
    df_q["quartos_label"] = df_q["quartos"].map(
        {1: "1 quarto", 2: "2 quartos", 3: "3 quartos", 4: "4+ quartos"}
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("none")
    ax.set_facecolor(BG)

    grupos_box = [
        df_q[df_q["quartos"] == q]["preco_m2"].dropna().values
        for q in [1, 2, 3, 4]
    ]
    labels_box = ["1 quarto", "2 quartos", "3 quartos", "4+ quartos"]
    validos = [(g, l) for g, l in zip(grupos_box, labels_box) if len(g) >= 3]

    if validos:
        bps = ax.boxplot(
            [v[0] for v in validos],
            labels=[v[1] for v in validos],
            patch_artist=True,
            medianprops=dict(color=DOURADO, lw=2.5),
            boxprops=dict(facecolor=AZUL, alpha=0.6),
            whiskerprops=dict(color=CINZA),
            capprops=dict(color=CINZA),
            flierprops=dict(marker="o", color=CINZA, alpha=0.4, markersize=3),
        )

    ax.set_ylabel("Preço por m² (R$)", fontsize=9, color=CINZA)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=CINZA, labelsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}".replace(",", ".")))
    ax.grid(axis="y", alpha=0.3, linestyle="--", color="#CBD5E0")
    ax.set_title(
        f"Preço por m² por tipologia — Ipatinga-MG | {DATA_REF}",
        fontsize=9.5, color="#0D1B2A", fontweight="bold", pad=10
    )
    plt.tight_layout()
    p3 = str(GRAFICO_DIR / "03_boxplot_quartos.png")
    fig.savefig(p3, dpi=180, bbox_inches="tight", facecolor="none")
    plt.close()
    arquivos["boxplot_quartos"] = p3
    print(f"  ✓ Gráfico 3: {p3}")

    # ── 4. Desconto vs BH ─────────────────────────────────────────────────────
    if len(df_bairros) > 0:
        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor("none")
        ax.set_facecolor(BG)

        top8 = df_bairros.head(8)
        x = range(len(top8))
        ax.bar(x, top8["mediana"], color=AZUL, label="Ipatinga (mediana)", zorder=2, width=0.4)
        ax.axhline(BH_M2, color=DOURADO, lw=2.5, linestyle="--", label=f"BH (FipeZAP dez/2025): R$ {BH_M2:,}".replace(",", "."), zorder=3)
        ax.set_xticks(list(x))
        ax.set_xticklabels(top8["bairro"], rotation=30, ha="right", fontsize=8.5)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", ".")))
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(colors=CINZA, labelsize=9)
        ax.legend(fontsize=9, framealpha=0.85)
        ax.grid(axis="y", alpha=0.3, linestyle="--", color="#CBD5E0")
        ax.set_title(
            f"Preço mediano m² Ipatinga vs. Belo Horizonte | {DATA_REF}",
            fontsize=9.5, color="#0D1B2A", fontweight="bold", pad=10
        )
        plt.tight_layout()
        p4 = str(GRAFICO_DIR / "04_desconto_bh.png")
        fig.savefig(p4, dpi=180, bbox_inches="tight", facecolor="none")
        plt.close()
        arquivos["desconto_bh"] = p4
        print(f"  ✓ Gráfico 4: {p4}")

    return arquivos


# ── EXPORTAR JSON PARA O DASHBOARD ────────────────────────────────────────────
def exportar_json(df, df_bairros, df_tipologia, df_composicao, caminho_csv):
    """
    Exporta todos os dados processados em JSON pronto para o dashboard.
    O pipeline.py usa este JSON para gerar o HTML atualizado.
    """
    pm2 = df["preco_m2"].dropna()

    # Trimestre atual
    mes = date.today().month
    trimestre = f"Q{((mes - 1) // 3) + 1}/{date.today().year}"

    payload = {
        "meta": {
            "edicao":        trimestre,
            "data_coleta":   DATA_REF,
            "n_total":       int(len(df)),
            "n_bairros":     int(len(df_bairros)),
            "portais":       df["portal"].value_counts().to_dict(),
            "fontes_macro": {
                "selic":          {"valor": SELIC,        "fonte": "Banco Central · mar/2026"},
                "ipca_12m":       {"valor": IPCA_12M,     "fonte": "IBGE · fev/2026"},
                "bh_m2":          {"valor": BH_M2,        "fonte": "FipeZAP · dez/2025"},
                "fipezap_2025":   {"valor": FIPEZAP_2025, "fonte": "ANOREG/DataZap · jan/2026"},
                "fipezap_2024":   {"valor": FIPEZAP_2024, "fonte": "ANOREG/DataZap · jan/2025"},
            },
        },
        "resumo_mercado": {
            "pm2_media":    round(float(pm2.mean())),
            "pm2_mediana":  round(float(pm2.median())),
            "pm2_dp":       round(float(pm2.std())),
            "pm2_q1":       round(float(pm2.quantile(0.25))),
            "pm2_q3":       round(float(pm2.quantile(0.75))),
            "pm2_min":      round(float(pm2.min())),
            "pm2_max":      round(float(pm2.max())),
            "valor_medio":  round(float(df["valor_anunciado"].median())),
            "area_mediana": round(float(df["area_m2"].median()), 1),
        },
        "bairros": df_bairros.to_dict(orient="records"),
        "tipologias": df_tipologia.to_dict(orient="records"),
        "composicao_oferta": df_composicao.to_dict(orient="records"),
    }

    caminho_json = OUTPUT_DIR / f"radar_dados_{trimestre.replace('/', '_')}.json"
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✅ JSON exportado: {caminho_json}")
    return caminho_json, payload


# ── RELATÓRIO DE QUALIDADE ─────────────────────────────────────────────────────
def relatorio_qualidade(df, df_bairros):
    """Imprime relatório de qualidade dos dados para auditoria."""
    print("\n" + "=" * 60)
    print("RELATÓRIO DE QUALIDADE DOS DADOS")
    print("=" * 60)
    print(f"Total de observações:     {len(df)}")
    print(f"Bairros identificados:    {df['bairro'].nunique()}")
    print(f"Portais representados:    {df['portal'].nunique()}")
    print(f"Período de coleta:        {df['data_coleta'].min()} a {df['data_coleta'].max()}")
    print(f"Completude área m²:       {df['area_m2'].notna().mean()*100:.1f}%")
    print(f"Completude quartos:       {df['quartos'].notna().mean()*100:.1f}%")
    print(f"Completude valor:         {df['valor_anunciado'].notna().mean()*100:.1f}%")
    print(f"\nPreço m² — resumo:")
    print(f"  Mínimo:   R$ {df['preco_m2'].min():,.0f}".replace(",", "."))
    print(f"  Q1:       R$ {df['preco_m2'].quantile(0.25):,.0f}".replace(",", "."))
    print(f"  Mediana:  R$ {df['preco_m2'].median():,.0f}".replace(",", "."))
    print(f"  Média:    R$ {df['preco_m2'].mean():,.0f}".replace(",", "."))
    print(f"  Q3:       R$ {df['preco_m2'].quantile(0.75):,.0f}".replace(",", "."))
    print(f"  Máximo:   R$ {df['preco_m2'].max():,.0f}".replace(",", "."))
    print(f"  Desvio p: R$ {df['preco_m2'].std():,.0f}".replace(",", "."))
    print(f"\nBairros com n < {N_MIN_BAIRRO} (excluídos da análise):")
    exc = df["bairro"].value_counts()[df["bairro"].value_counts() < N_MIN_BAIRRO]
    for b, n in exc.items():
        print(f"  {b}: {n} obs.")
    print("=" * 60)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def analisar(caminho_csv):
    print("=" * 60)
    print("ANÁLISE ESTATÍSTICA — RADAR IMOBILIÁRIO VALE DO AÇO")
    print("=" * 60)

    df           = carregar(caminho_csv)
    df_bairros   = estatisticas_bairro(df)
    df_tipologia = estatisticas_tipologia(df)
    df_composicao = composicao_oferta(df)

    relatorio_qualidade(df, df_bairros)

    print("\n📈 Gerando gráficos...")
    arquivos_graficos = gerar_graficos(df, df_bairros, df_tipologia)

    print("\n💾 Exportando dados para o dashboard...")
    caminho_json, payload = exportar_json(
        df, df_bairros, df_tipologia, df_composicao, caminho_csv
    )

    return payload, caminho_json, arquivos_graficos


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Busca o CSV mais recente na pasta dados/
        csvs = sorted(Path("dados").glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not csvs:
            print("❌ Nenhum CSV encontrado em dados/. Execute coletor.py primeiro.")
            sys.exit(1)
        caminho = str(csvs[0])
        print(f"ℹ️  Usando CSV mais recente: {caminho}")
    else:
        caminho = sys.argv[1]

    payload, json_path, graficos = analisar(caminho)
    print(f"\nPróximo passo: python gerar_dashboard.py {json_path}")
