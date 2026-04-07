#!/bin/bash
# ============================================================
# deploy.sh — Radar Imobiliário · Vale do Aço
# Uso: ./deploy.sh "mensagem do commit"
# Exemplo: ./deploy.sh "Q2 2026: atualização de preços"
# ============================================================

set -e

MENSAGEM=${1:-"Atualização do dashboard"}
DATA=$(date +"%d/%m/%Y %H:%M")

echo ""
echo "=== Radar Imobiliário · Vale do Aço ==="
echo "Deploy em: $DATA"
echo "Commit: $MENSAGEM"
echo ""

# Adiciona todos os arquivos modificados
git add -A

# Commit com mensagem e data automática
git commit -m "$MENSAGEM [$DATA]"

# Push para o GitHub (branch main)
git push origin main

echo ""
echo "✓ Deploy concluído."
echo "✓ Dashboard disponível em:"
echo "  https://marinhobusiness.github.io/radar-vale-do-aco"
echo ""
echo "  Aguarde 1-2 minutos para o GitHub Pages processar."
echo ""
