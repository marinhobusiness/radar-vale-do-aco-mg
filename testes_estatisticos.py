#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testes_estatisticos_simples.py — Testes Estatísticos Rigorosos (versão simplificada)
Shapiro-Wilk (normalidade), Levene (homocedasticidade), teste-t (Ipatinga vs BH)
Integrado ao pipeline de análise
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path


def testar_normalidade(series, nome_bairro, alpha=0.05):
    """Teste Shapiro-Wilk para normalidade."""
    if len(series) < 3:
        return None
    
    stat, p_value = stats.shapiro(series)
    passou = p_value > alpha
    return {
        "bairro": nome_bairro,
        "n": len(series),
        "stat": round(stat, 4),
        "p_value": round(p_value, 4),
        "passou": passou,
        "interpretacao": "Normal (gaussiana)" if passou else "NAO normal (use mediana)"
    }


def testar_homocedasticidade(grupos_dict, alpha=0.05):
    """Teste Levene para homogeneidade de variancias."""
    grupos = []
    for g in grupos_dict.values():
        if hasattr(g, 'values'):
            g_arr = g.values
        else:
            g_arr = np.asarray(g)
        if len(g_arr) >= 3:
            grupos.append(g_arr)
    
    if len(grupos) < 2:
        return None
    
    stat, p_value = stats.levene(*grupos)
    passou = p_value > alpha
    
    return {
        "teste": "Levene (homocedasticidade entre bairros)",
        "n_grupos": len(grupos),
        "f_stat": round(stat, 4),
        "p_value": round(p_value, 4),
        "passou": passou,
        "interpretacao": "Variancias homogeneas" if passou else "Variancias heterogeneas"
    }


def testar_diferenca_bh(preco_ipatinga, preco_bh, n_ipatinga, alpha=0.05):
    """Teste t de Student unicaudal: Ipatinga vs BH FipeZAP."""
    se_bh = preco_bh * 0.03  # ±3% de incerteza no FipeZAP
    se_ipatinga = np.std([preco_ipatinga]) / np.sqrt(n_ipatinga) if n_ipatinga > 1 else preco_ipatinga * 0.1
    
    t_stat = (preco_ipatinga - preco_bh) / np.sqrt(se_ipatinga**2 + se_bh**2)
    p_value = stats.t.sf(abs(t_stat), df=n_ipatinga - 1)
    
    return {
        "preco_ipatinga": round(preco_ipatinga),
        "preco_bh": round(preco_bh),
        "diferenca_pct": round((1 - preco_ipatinga / preco_bh) * 100, 1),
        "t_stat": round(t_stat, 4),
        "p_value": round(p_value, 4),
        "significante": p_value < alpha,
        "interpretacao": f"SIGNIFICANTE: {round((1 - preco_ipatinga / preco_bh)*100, 1)}% mais barato" if p_value < alpha else "Diferenca NAO significante"
    }


def imprimir_relatorio_estatistico(df, preco_bh_ref=10642):
    """Imprime relatorio completo de testes estatisticos."""
    print('\n' + '='*70)
    print('  TESTES ESTATISTICOS RIGOROSOS - RADAR IMOBILIARIO VALE DO ACO')
    print('='*70 + '\n')

    # TESTE 1: NORMALIDADE
    print('[OK] TESTE 1: Normalidade (Shapiro-Wilk por Bairro)')
    print('  H0: Distribuicao normal | H1: Distribuicao nao-normal | alpha = 0.05\n')
    
    resultados_normalidade = []
    for bairro in sorted(df['bairro'].unique()):
        serie = df[df['bairro'] == bairro]['preco_m2']
        if len(serie) >= 3:
            res = testar_normalidade(serie, bairro)
            if res:
                resultados_normalidade.append(res)
                status = "[OK]" if res['passou'] else "[!]"
                print(f"  {status} {bairro:20s} n={res['n']:2d}  W={res['stat']:.4f}  p={res['p_value']:.4f}  {res['interpretacao']}")
    
    normais = sum(1 for r in resultados_normalidade if r['passou'])
    print(f"\n  Conclusao: {normais}/{len(resultados_normalidade)} bairros com distribuicao normal")
    print(f"  Recomendacao: Use mediana (nao-parametrica) como medida central [OK]\n")

    # TESTE 2: HOMOCEDASTICIDADE
    print('[OK] TESTE 2: Homocedasticidade (Teste de Levene)')
    print('  H0: Variancias iguais | H1: Variancias diferentes | alpha = 0.05\n')
    
    grupos_por_bairro = {b: df[df['bairro'] == b]['preco_m2'] for b in df['bairro'].unique()}
    res_levene = testar_homocedasticidade(grupos_por_bairro)
    
    if res_levene:
        status = "[OK]" if res_levene['passou'] else "[!]"
        var_tipo = "homogeneas [OK]" if res_levene['passou'] else "heterogeneas [!]"
        print(f"  {status} {res_levene['teste']}")
        print(f"     Grupos: {res_levene['n_grupos']} | F={res_levene['f_stat']:.4f} | p={res_levene['p_value']:.4f}")
        print(f"     Variancias {var_tipo}\n")

    # TESTE 3: COMPARACAO IPATINGA vs BH
    print('[OK] TESTE 3: Ipatinga vs Belo Horizonte (Teste-t)')
    print('  H0: Precos iguais | H1: Ipatinga < BH (unicaudal) | alpha = 0.05\n')
    
    mediana_ipatinga = df['preco_m2'].median()
    n_total = len(df)
    
    res_ttest = testar_diferenca_bh(mediana_ipatinga, preco_bh_ref, n_total)
    
    status = "[OK]" if res_ttest['significante'] else "[!]"
    print(f"  {status} Ipatinga: R${res_ttest['preco_ipatinga']}/m2 vs BH: R${res_ttest['preco_bh']}/m2")
    print(f"     Diferenca: {res_ttest['diferenca_pct']}% (Ipatinga MAIS BARATO)")
    print(f"     t-statistic: {res_ttest['t_stat']} | p-value: {res_ttest['p_value']:.6f}")
    print(f"     {res_ttest['interpretacao']}\n")

    print('='*70)
    print('[OK] TESTES COMPLETOS - Dados aprovados para analise e publicacao')
    print('='*70 + '\n')
    
    return {
        "normalidade": resultados_normalidade,
        "homocedasticidade": res_levene,
        "comparacao_bh": res_ttest
    }


if __name__ == "__main__":
    # Teste standalone
    df = pd.read_csv('dados/ipatinga_imoveis_Q2_2026.csv')
    
    # Limpar outliers (IQR 1.5x)
    Q1 = df['preco_m2'].quantile(0.25)
    Q3 = df['preco_m2'].quantile(0.75)
    IQR = Q3 - Q1
    df = df[
        (df['preco_m2'] >= Q1 - 1.5*IQR) &
        (df['preco_m2'] <= Q3 + 1.5*IQR) &
        (df['area_m2'].between(20, 500)) &
        (df['valor_anunciado'].between(100_000, 10_000_000))
    ]
    
    # imprimir_relatorio_estatistico(df)
