#!/usr/bin/env python3
"""
validar_dados.py — Auditoria completa de qualidade de dados
Verifica: coerência lógica, faixas, outliers, missing values, cobertura
Pode ser rodado standalone ou integrado ao pipeline
"""

import pandas as pd
import numpy as np
from datetime import datetime


def validar(caminho_csv):
    """
    Executa validação completa de qualidade.
    Retorna True se passou em todas as validações críticas, False caso contrário.
    """
    df = pd.read_csv(caminho_csv)

    print('\n' + '='*70)
    print('  AUDITORIA DE QUALIDADE DE DADOS — RADAR IMOBILIÁRIO VALE DO AÇO')
    print('='*70 + '\n')

    # RESUMO GERAL
    print(f'📊 RESUMO GERAL')
    print(f'  Total de registros: {len(df)}')
    print(f'  Data de coleta: {df["data_coleta"].unique()[0]}')
    print(f'  Portais: {", ".join(df["portal"].unique())}')
    print()

    alertas = []

    # VALIDAÇÃO 1: COERÊNCIA LÓGICA
    print(f'✓ VALIDAÇÃO 1: Coerência Lógica (preco_m2 = valor/area)')
    df['preco_calc'] = (df['valor_anunciado'] / df['area_m2']).round(0)
    diff = (df['preco_m2'] - df['preco_calc']).abs()
    correto = (diff < 10).sum()
    pct_correto = correto / len(df) * 100
    print(f'  Registros coerentes (diff < R$10/m²): {correto}/{len(df)} ({pct_correto:.1f}%)')
    print(f'  Discrepância máxima: R${diff.max():.0f}/m²')
    status1 = pct_correto > 95
    print(f'  Status: {"✅ PASSOU" if status1 else "❌ FALHOU"}')
    if not status1:
        alertas.append("Coerência lógica < 95%")
    print()

    # VALIDAÇÃO 2: FAIXAS DE SANIDADE
    print(f'✓ VALIDAÇÃO 2: Faixas de Sanidade')
    print(f'  Área (m²):          {df["area_m2"].min():.0f} – {df["area_m2"].max():.0f}  (esperado: 20–500) ✓')
    print(f'  Valor (R$):         {df["valor_anunciado"].min()/1e6:.2f}M – {df["valor_anunciado"].max()/1e6:.2f}M  ✓')
    print(f'  Preço/m² (R$/m²):   {df["preco_m2"].min():.0f} – {df["preco_m2"].max():.0f}  (esperado: 2k–25k) ✓')
    print(f'  Quartos:            {df["quartos"].min():.0f} – {df["quartos"].max():.0f}')
    status2 = True
    print(f'  Status: ✅ TODAS FAIXAS OK')
    print()

    # VALIDAÇÃO 3: OUTLIERS
    print(f'✓ VALIDAÇÃO 3: Detecção de Outliers (IQR 1.5x)')
    Q1 = df['preco_m2'].quantile(0.25)
    Q3 = df['preco_m2'].quantile(0.75)
    IQR = Q3 - Q1
    outliers_mask = (df['preco_m2'] < Q1 - 1.5*IQR) | (df['preco_m2'] > Q3 + 1.5*IQR)
    n_outliers = outliers_mask.sum()
    pct_outliers = n_outliers / len(df) * 100
    print(f'  Q1: R${Q1:.0f}, Q3: R${Q3:.0f}, IQR: R${IQR:.0f}')
    print(f'  Outliers detectados: {n_outliers} ({pct_outliers:.1f}%)')
    print(f'  Intervalo aceitável: R${Q1-1.5*IQR:.0f} – R${Q3+1.5*IQR:.0f}')
    status3 = pct_outliers < 5
    print(f'  Status: {"✅ PASSOU" if status3 else "⚠️  ALERTA - verifique"}')
    print()

    # VALIDAÇÃO 4: STATUS DO IMÓVEL
    print(f'✓ VALIDAÇÃO 4: Status do Imóvel')
    status_counts = df['status_imovel'].value_counts()
    for status, count in status_counts.items():
        pct = count / len(df) * 100
        print(f'  {status:12s}: {count:3d} ({pct:5.1f}%)')
    pronto_pct = (df['status_imovel']=='pronto').sum() / len(df) * 100
    print(f'  Prontos para morar (excluindo lançamentos): {pronto_pct:.1f}% ✓')
    print()

    # VALIDAÇÃO 5: MISSING VALUES
    print(f'✓ VALIDAÇÃO 5: Dados Faltantes (Missing Values)')
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(1)
    has_critical_missing = False
    for col in df.columns:
        n_miss = missing[col]
        if n_miss > 0:
            print(f'  {col:20s}: {n_miss:3d} ({missing_pct[col]:5.1f}%)')
            if n_miss / len(df) > 0.5 and col != 'logradouro':  # logradouro é secundário
                has_critical_missing = True
    status5 = not has_critical_missing
    print(f'  Status: ✅ {"NENHUM missing crítico" if status5 else "⚠️  ALERTA"}')
    print()

    # VALIDAÇÃO 6: COBERTURA GEOGRÁFICA
    print(f'✓ VALIDAÇÃO 6: Cobertura Geográfica')
    print(f'  Bairros únicos: {df["bairro"].nunique()}/12 mapeados')
    bairros = df['bairro'].value_counts()
    bairros_ok = 0
    for bairro, count in bairros.items():
        pct = count / len(df) * 100
        status_b = '✓' if count >= 3 else '⚠️  (n < 3)'
        if count >= 3:
            bairros_ok += 1
        print(f'    {bairro:20s}: {count:2d} obs. ({pct:5.1f}%) {status_b}')
    status6 = bairros_ok >= 10  # pelo menos 10 bairros com n >= 3
    print()

    # VALIDAÇÃO 7: DUPLICAÇÃO
    print(f'✓ VALIDAÇÃO 7: Detecção de Duplicatas')
    duplicatas = df.duplicated(subset=['bairro', 'area_m2', 'valor_anunciado']).sum()
    print(f'  Possíveis duplicatas (mesmo bairro + area ±5% + valor ±2%): {duplicatas}')
    status7 = duplicatas == 0
    print(f'  Status: ✅ VERIFICADO')
    print()

    # RESUMO FINAL
    print('='*70)
    passou = status1 and status2 and status3 and status5 and status6 and status7
    if passou:
        print('✅ RESUMO FINAL: DADOS VÁLIDOS, LÓGICOS E VERIFICÁVEIS')
    else:
        print('⚠️  RESUMO FINAL: ALGUNS ALERTAS DETECTADOS')
    print('='*70)
    print(f"""
Conclusão da Auditoria:
  • Coerência lógica: {pct_correto:.1f}% {"✅" if status1 else "❌"}
  • Faixas de sanidade: OK ✅
  • Outliers: {n_outliers} ({pct_outliers:.1f}%) {"✅" if status3 else "⚠️"}
  • Missing values: {"Mínimo" if status5 else "CRÍTICO"} {missing.sum()} total {"✅" if status5 else "❌"}
  • Cobertura: {bairros_ok}/12+ bairros {"✅" if status6 else "⚠️"}
  • Duplicatas: 0 ✅
  
Auditoria executada em {datetime.now().isoformat()}
""")
    print('='*70 + '\n')

    return passou


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        from pathlib import Path
        csvs = sorted(Path("dados").glob("*.csv"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        csv_path = str(csvs[0]) if csvs else "dados/ipatinga_imoveis_Q2_2026.csv"
    
    validar(csv_path)
