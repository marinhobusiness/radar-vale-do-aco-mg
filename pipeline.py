#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline.py — Radar Imobiliário do Vale do Aço
Orquestra coleta → análise → dashboard → publicação
Uso: python pipeline.py [--paginas N] [--kaggle] [--sem-push]

Autor: Wederson Marinho · Data Scientist
"""

import sys
import os

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding="utf-8")

import time
import argparse
from pathlib import Path
from datetime import date


def banner():
    print("=" * 66)
    print("  RADAR IMOBILIÁRIO · VALE DO AÇO · PIPELINE")
    print("  Wederson Marinho · Data Scientist")
    print("=" * 66)
    print()


def parse_args():
    p = argparse.ArgumentParser(description="Pipeline do Radar Imobiliário")
    p.add_argument("--paginas",   type=int, default=10,
                   help="Páginas por portal (default: 10, ~250 anúncios/portal)")
    p.add_argument("--kaggle",    action="store_true",
                   help="Publicar dataset no Kaggle após análise")
    p.add_argument("--sem-push",  action="store_true",
                   help="Gerar arquivos sem fazer git push")
    p.add_argument("--so-analisar", action="store_true",
                   help="Pular coleta, usar CSV existente mais recente")
    p.add_argument("--csv",       type=str, default=None,
                   help="Usar CSV específico em vez de coletar")
    p.add_argument("--mensagem",  type=str, default=None,
                   help="Mensagem customizada para o commit")
    return p.parse_args()


def etapa(numero, total, nome):
    print(f"\n{'═'*60}")
    print(f"  ETAPA {numero}/{total}: {nome}")
    print(f"{'═'*60}")


def verificar_dependencias():
    """Verifica se as dependências Python estão instaladas."""
    deps = {
        "requests":    "requests",
        "pandas":      "pandas",
        "numpy":       "numpy",
        "scipy":       "scipy",
        "matplotlib":  "matplotlib",
    }
    faltando = []
    for modulo, pacote in deps.items():
        try:
            __import__(modulo)
        except ImportError:
            faltando.append(pacote)

    if faltando:
        print(f"❌ Dependências ausentes: {', '.join(faltando)}")
        print(f"   Execute: pip install {' '.join(faltando)}")
        return False
    return True


def main():
    banner()
    args = parse_args()
    inicio = time.time()

    print(f"Data: {date.today().isoformat()}")
    print(f"Configuração:")
    print(f"  Páginas por portal:  {args.paginas} (~{args.paginas * 24} anúncios/portal)")
    print(f"  Publicar no Kaggle:  {'sim' if args.kaggle else 'não'}")
    print(f"  Git push:            {'não' if args.sem_push else 'sim'}")
    print(f"  Só analisar:         {'sim' if args.so_analisar else 'não'}")

    # Verificar dependências
    if not verificar_dependencias():
        sys.exit(1)

    caminho_csv  = args.csv
    caminho_json = None

    # ── ETAPA 1: COLETA ──────────────────────────────────────────────────────
    if not args.so_analisar and not caminho_csv:
        etapa(1, 4, "COLETA DE DADOS — Zap / VivaReal / OLX")

        from coletor import coletar_tudo
        dados, caminho_csv = coletar_tudo(paginas_por_portal=args.paginas)

        if not dados:
            print("\n❌ Coleta retornou 0 registros.")
            print("   Possíveis causas:")
            print("   1. Sem conexão com a internet")
            print("   2. Portais bloquearam o IP (aguarde alguns minutos)")
            print("   3. Estrutura da API mudou (veja coletor.py)")
            sys.exit(1)

        print(f"\n  ✅ Coleta concluída: {len(dados)} anúncios únicos")

    else:
        etapa(1, 4, "COLETA — pulada (usando CSV existente)")
        if not caminho_csv:
            csvs = sorted(Path("dados").glob("*.csv"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            if not csvs:
                print("❌ Nenhum CSV em dados/. Execute sem --so-analisar primeiro.")
                sys.exit(1)
            caminho_csv = str(csvs[0])
        print(f"  CSV: {caminho_csv}")

    # ── ETAPA 1B: VALIDAÇÃO ─────────────────────────────────────────────────
    etapa("1B", 4, "VALIDAÇÃO DE QUALIDADE DE DADOS")

    from validar_dados import validar
    validacao_ok = validar(caminho_csv)
    if not validacao_ok:
        print("\n⚠️  Validação retornou alertas. Continuando com cautela...")

    # ── ETAPA 1C: TESTES ESTATÍSTICOS ────────────────────────────────────────
    etapa("1C", 4, "TESTES ESTATÍSTICOS RIGOROSOS")

    try:
        from testes_estatisticos import imprimir_relatorio_estatistico
        import pandas as pd
        df_teste = pd.read_csv(caminho_csv)
        
        # Limpar conforme pipeline
        Q1 = df_teste['preco_m2'].quantile(0.25)
        Q3 = df_teste['preco_m2'].quantile(0.75)
        IQR = Q3 - Q1
        df_teste = df_teste[
            (df_teste['preco_m2'] >= Q1 - 1.5*IQR) &
            (df_teste['preco_m2'] <= Q3 + 1.5*IQR) &
            (df_teste['area_m2'].between(20, 500)) &
            (df_teste['valor_anunciado'].between(100_000, 10_000_000))
        ]
        
        imprimir_relatorio_estatistico(df_teste)
        print(f"\n  [i] Salvo em: dados/sensibilidade_Q2_2026.json")
    except ImportError as e:
        print(f"  [i] scipy nao instalado ainda, pulando testes (pip em andamento)")
    except Exception as e:
        print(f"  [!] Erro: {str(e)}")
        print("     Execute manualmente: python testes_estatisticos.py")

    # ── ETAPA 2: ANÁLISE ─────────────────────────────────────────────────────
    etapa(2, 4, "ANÁLISE ESTATÍSTICA")

    from analisar import analisar
    payload, caminho_json, graficos = analisar(caminho_csv)
    n_total   = payload["meta"]["n_total"]
    n_bairros = payload["meta"]["n_bairros"]
    print(f"\n  ✅ Análise concluída: {n_total} obs · {n_bairros} bairros")

    # ── ETAPA 3: DASHBOARD ───────────────────────────────────────────────────
    etapa(3, 4, "GERAÇÃO DO DASHBOARD HTML")

    from gerar_dashboard import gerar
    caminho_html = gerar(caminho_json)
    print(f"\n  ✅ Dashboard gerado: {caminho_html}")

    # ── ETAPA 4: PUBLICAÇÃO ──────────────────────────────────────────────────
    etapa(4, 4, "PUBLICAÇÃO")

    from publicar import publicar
    if not args.sem_push:
        edicao = payload["meta"]["edicao"]
        mensagem = args.mensagem or f"Radar Imobiliário {edicao} · n={n_total} · {date.today().isoformat()}"
        publicar(mensagem=mensagem, kaggle=args.kaggle)
    else:
        print("  ℹ️  Git push pulado (--sem-push)")
        print(f"  Para publicar manualmente:")
        print(f"    git add -A")
        print(f"    git commit -m 'Radar Imobiliário {date.today()}'")
        print(f"    git push origin main")

    # ── RESUMO FINAL ─────────────────────────────────────────────────────────
    elapsed = time.time() - inicio
    mins    = int(elapsed // 60)
    segs    = int(elapsed % 60)

    resumo = payload["resumo_mercado"]
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  PIPELINE CONCLUÍDO em {mins}min {segs}s
╠══════════════════════════════════════════════════════════════╣
║  Edição:           {payload['meta']['edicao']}
║  Observações:      {n_total} anúncios únicos
║  Bairros analisados: {n_bairros}
║  Preço mediano m²: R$ {resumo['pm2_mediana']:,}
║  Desvio padrão:    R$ {resumo['pm2_dp']:,}
╠══════════════════════════════════════════════════════════════╣
║  Arquivos gerados:
║    {caminho_csv}
║    {caminho_json}
║    index.html
╠══════════════════════════════════════════════════════════════╣
║  Dashboard:
║    https://marinhobusiness.github.io/radar-vale-do-aco
╚══════════════════════════════════════════════════════════════╝
""".replace(",", "."))


if __name__ == "__main__":
    main()
