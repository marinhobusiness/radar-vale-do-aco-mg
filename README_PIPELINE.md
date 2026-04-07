# Pipeline · Radar Imobiliário Vale do Aço

Pipeline completo de coleta, análise e publicação do Radar Imobiliário do Vale do Aço.
Executa em sequência: coleta de dados reais → análise estatística → geração do dashboard → git push.

## Setup (uma vez)

```bash
pip install -r requirements.txt
```

## Uso

### Rodar o pipeline completo (recomendado)
```bash
python pipeline.py
```

### Opções avançadas
```bash
# Mais páginas = mais dados (cada página ≈ 24 anúncios por portal)
python pipeline.py --paginas 15

# Publicar também no Kaggle
python pipeline.py --kaggle

# Gerar arquivos sem fazer git push (para revisar antes)
python pipeline.py --sem-push

# Usar CSV já existente (pular coleta)
python pipeline.py --so-analisar

# Usar CSV específico
python pipeline.py --csv dados/ipatinga_imoveis_Q2_2026.csv
```

### Rodar etapas individualmente
```bash
python coletor.py                        # coleta → salva CSV em dados/
python analisar.py dados/arquivo.csv    # análise → salva JSON e gráficos
python gerar_dashboard.py dados/arquivo.json  # gera index.html
python publicar.py                      # git push
python publicar.py --kaggle             # git push + Kaggle
python publicar.py --atualizar-readme 10.5281/zenodo.XXXXXXX  # adiciona DOI
```

## Estrutura de arquivos gerados

```
dados/
  ipatinga_imoveis_Q2_2026.csv     ← dataset bruto (para Kaggle + Zenodo)
  radar_dados_Q2_2026.json         ← dados processados (para o dashboard)
  graficos/
    01_preco_bairro.png
    02_distribuicao.png
    03_boxplot_quartos.png
    04_desconto_bh.png
index.html                          ← dashboard atualizado (para GitHub Pages)
```

## Notas técnicas

- **Portais:** Zap Imóveis, VivaReal e OLX via APIs internas (descobertas por DevTools)
- **Delay:** 2.5–5s entre requests para não sobrecarregar os servidores
- **Deduplicação:** Remove duplicatas cruzadas entre portais (mesmo bairro + área + valor ±2%)
- **Outliers:** Removidos pelo método IQR 1.5× após deduplicação
- **n mínimo:** Bairros com menos de 3 observações são excluídos da análise estatística
- **IC 95%:** Calculado via distribuição t de Student

## Autor

Wederson Marinho · Data Scientist
CRECI-MG 58.263-F · CNAI 51.239 · ORCID: 0009-0004-6401-3465
marinhobusiness@gmail.com · linkedin.com/in/marinhobusiness
