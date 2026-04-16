# Radar Imobiliário · Vale do Aço

**Análise quantitativa do mercado imobiliário de Ipatinga-MG**
Anúncios ativos verificados · Publicação trimestral · Código aberto

🌐 **Dashboard ao vivo:** [marinhobusiness.github.io/radar-vale-do-aco-mg](https://marinhobusiness.github.io/radar-vale-do-aco-mg)

📊 **Dataset com DOI:** [Zenodo](https://zenodo.org) (DOI: 10.5281/zenodo.XXXXXXX — em progresso)

---

## O que é este projeto

O **Radar Imobiliário do Vale do Aço** coleta anúncios públicos de apartamentos à venda em Ipatinga-MG nos portais Zap Imóveis, VivaReal e OLX, aplica limpeza estatística robusta e publica um dashboard interativo com preço mediano por m² por bairro, intervalo de confiança 95%, distribuição de preços e comparativo com Belo Horizonte (FipeZAP).

O pipeline é 100% automatizável, reproduzível e auditável — todos os dados brutos são publicados junto com o código.

Mantido por **Wederson Marinho** — Data Scientist | Perito Judicial | Especialista em Mercado Imobiliário · CRECI-MG 58.263-F · CNAI 51.239 · ORCID [0009-0004-6401-3465](https://orcid.org/0009-0004-6401-3465).

---

## Edições publicadas

| Edição | Data | n (obs.) | Bairros | Dashboard |
|--------|------|----------|---------|-----------|
| Q2 2026 | abr/2026 | 62 | 12 | [Ver](https://marinhobusiness.github.io/radar-vale-do-aco-mg) |

---

## Metodologia

### Escopo

- **Cidade:** Ipatinga, MG
- **Tipo:** Apartamentos residenciais
- **Operação:** Venda
- **Status:** Anúncios ativos de imóveis **prontos para morar** (usados e novos entregues)
- **Período:** Coleta pontual trimestral

> **Nota sobre lançamentos na planta:** Apartamentos em fase de lançamento (off-plan) são identificados e excluídos da amostra principal, pois praticam preços sistematicamente superiores (tipicamente R$ 9.000–12.000/m² em Ipatinga em 2025/2026) que não refletem o mercado de imóveis disponíveis para entrega imediata. Quando presentes na coleta, são classificados como `status_imovel = lancamento` no CSV e removidos pelo filtro IQR 1,5× antes da análise. Essa separação é intencional e documentada.

### Pipeline de dados

```
Coleta (coletor.py)
  └─ Zap Imóveis API interna (glue-api.zapimoveis.com.br)
  └─ VivaReal API interna  (glue-api.vivareal.com.br)
  └─ OLX API de busca
        │
        ▼
Deduplicação cruzada entre portais
  Critério: mesmo bairro + área ±5 m² + valor ±2%
        │
        ▼
Análise (analisar.py)
  └─ Remoção de outliers: IQR 1,5×
  └─ Filtro de sanidade: área 20–500 m², valor R$ 100k–10M, pm² R$ 2.000–25.000/m²
  └─ Estatísticas por bairro: n ≥ 3 observações obrigatórias
  └─ IC 95% via distribuição t de Student (scipy.stats)
        │
        ▼
Dashboard (gerar_dashboard.py) → index.html → GitHub Pages
```

### Indicadores calculados

| Indicador | Método |
|-----------|--------|
| Preço mediano m² | Mediana amostral por bairro |
| Intervalo de confiança 95% | Distribuição t de Student (`scipy.stats.t.interval`) |
| Desvio padrão | Desvio padrão amostral |
| Desconto vs BH | `(1 - mediana_ipatinga / pm2_BH) × 100%` |
| Cap rate estimado | `(valor × 0,42% × 12) / valor` — referência FipeZAP locação |

### Testes Estatísticos (Nível 2 — Rigor Científico)

Todos os bairros foram submetidos a testes de normalidade, homocedasticidade e significância:

| Teste | Método | Resultado | Aprovado |
|-------|--------|-----------|----------|
| Normalidade | Shapiro-Wilk (alpha=0.05) | 11/12 bairros normal | ✅ |
| Homocedasticidade | Levene (alpha=0.05) | p=0.189 | ✅ |
| Significância vs BH | Teste-t unicaudal | p<0.001 | ✅ |
| **Conclusão** | Ipatinga **53% mais barato** que BH | Estatisticamente significante | ✅ |

Execute `python testes_estatisticos.py` para relatório completo com valores exatos.

---

### Validação de Dados

Todos os dados brutos são submetidos a auditoria de qualidade automatizada antes da publicação. Execute `python validar_dados.py` para verificar:

| Validação | Critério | Status |
|-----------|----------|--------|
| Coerência lógica | `preco_m2 = valor_anunciado / area_m2` com discrepância < R$10/m² | ✅ 100% (65/65 registros) |
| Faixas de sanidade | Área 20–500 m², valor R$100k–10M, preço/m² R$2k–25k | ✅ OK |
| Outliers | IQR 1,5× (detecta 4,6% de casos extremos) | ✅ OK |
| Missing values | Apenas `logradouro` (90,8%), não crítico para análise | ✅ Mínimo |
| Cobertura | 15 bairros, 65 observações, 86,2% prontos para morar | ✅ OK |
| Duplicatas | Verificação por bairro + área ±5% + valor ±2% | ✅ 0 duplicatas |

**Conclusão:** Dados prontos para análise estatística e publicação.

### Limitações declaradas

1. **Preço anunciado ≠ preço de transação.** Os dados refletem o preço pedido (asking price), não o valor escriturado. O desconto médio de negociação no Brasil é de 5–12% (SECOVI-SP).
2. **Amostra trimestral.** A coleta é pontual — variações intra-trimestrais não são capturadas.
3. **n por bairro.** Bairros com menos de 3 observações são excluídos da análise estatística. Resultados de bairros com n < 10 devem ser interpretados com cautela.
4. **Abordagem de preços anunciados.** A metodologia é compatível com a utilizada pelo Índice FipeZAP para cidades monitoradas (preço/m² de anúncios ativos), mas **não é o índice FipeZAP** — Ipatinga não integra o painel oficial. A comparação com BH usa o valor FipeZAP dez/2025 como referência externa.
5. **Disponibilidade das APIs.** Os portais Zap/VivaReal/OLX podem alterar ou bloquear seus endpoints sem aviso. O pipeline inclui tratamento de erros e fallback para CSV existente (`--so-analisar`).

---

## Reprodução

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar pipeline completo (requer acesso às APIs)
python pipeline.py

# 3. Ou apenas reanalisar CSV já existente
python pipeline.py --so-analisar

# 4. Ver opções
python pipeline.py --help
```

---

## Estrutura de arquivos

```
radar-vale-do-aco/
├── pipeline.py              # orquestrador
├── coletor.py               # coleta Zap / VivaReal / OLX
├── analisar.py              # análise estatística
├── gerar_dashboard.py       # geração do index.html
├── publicar.py              # git push + Kaggle + instruções Zenodo
├── requirements.txt
├── index.html               # dashboard publicado (GitHub Pages)
└── dados/
    ├── ipatinga_imoveis_Q2_2026.csv   # dataset bruto
    ├── radar_dados_Q2_2026.json       # dados processados
    └── graficos/
        ├── 01_preco_bairro.png
        ├── 02_distribuicao.png
        ├── 03_boxplot_quartos.png
        └── 04_desconto_bh.png
```

---

## Dataset

O arquivo CSV bruto (`dados/ipatinga_imoveis_Q2_2026.csv`) contém os seguintes campos:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `bairro` | string | Bairro identificado |
| `tipo` | string | Tipo do imóvel (APARTMENT, HOME…) |
| `quartos` | int | Número de dormitórios |
| `banheiros` | int | Número de banheiros |
| `area_m2` | float | Área privativa declarada (m²) |
| `valor_anunciado` | int | Preço pedido (R$) |
| `preco_m2` | int | Preço por m² calculado |
| `logradouro` | string | Logradouro (quando disponível) |
| `portal` | string | Portal de origem |
| `data_coleta` | date | Data da coleta |
| `id_anuncio` | string | ID original no portal |
| `titulo` | string | Título do anúncio (primeiros 120 caracteres) |

**Licença do dataset:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)

---

## Citação

### ABNT NBR 6023

```
MARINHO, Wederson. Radar Imobiliário do Vale do Aço: análise quantitativa
do mercado imobiliário de Ipatinga-MG — Q2 2026. Ipatinga: 2026.
Disponível em: https://marinhobusiness.github.io/radar-vale-do-aco.
Acesso em: abr. 2026.
```

### BibTeX

```bibtex
@dataset{marinho2026radar,
  author    = {Marinho, Wederson},
  title     = {Radar Imobili{\'a}rio do Vale do A{\c{c}}o -- Q2 2026},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/marinhobusiness/radar-vale-do-aco},
  license   = {CC BY 4.0}
}
```

---

## Aviso legal

Este relatório é de distribuição gratuita. Livre reprodução com atribuição ao autor.

**Não constitui** recomendação de investimento, laudo técnico de avaliação imobiliária (PTAM) nem substituição a consulta com profissional habilitado CRECI/CNAI. Para laudos com validade jurídica, consulte avaliador credenciado conforme ABNT NBR 14653.

---

## Contato

**Wederson Marinho** — Data Scientist | Perito Judicial | Especialista em Mercado Imobiliário | Corretor de Imóveis
- Email: marinhobusiness@gmail.com
- LinkedIn: [linkedin.com/in/marinhobusiness](https://linkedin.com/in/marinhobusiness)
- ORCID: [0009-0004-6401-3465](https://orcid.org/0009-0004-6401-3465)
- CRECI-MG 58.263-F · CNAI 51.239
