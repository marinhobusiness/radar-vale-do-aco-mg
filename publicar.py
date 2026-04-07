"""
publicar.py — Radar Imobiliário do Vale do Aço
Publica o dashboard no GitHub Pages e opcionalmente no Zenodo e Kaggle
Autor: Wederson Marinho · Data Scientist
"""

import subprocess
import json
import os
import sys
import shutil
from pathlib import Path
from datetime import date

REPO_DIR = Path(".")


# ── GIT ───────────────────────────────────────────────────────────────────────
def git_status():
    """Verifica se há alterações para commitar."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    return result.stdout.strip()


def git_push(mensagem=None):
    """
    Adiciona todos os arquivos modificados, commita e faz push.
    Retorna True se bem-sucedido.
    """
    if not mensagem:
        trimestre = f"Q{((date.today().month - 1) // 3) + 1}/{date.today().year}"
        mensagem = f"Radar Imobiliário · {trimestre} · {date.today().isoformat()}"

    status = git_status()
    if not status:
        print("ℹ️  Git: nenhuma alteração detectada. Nada a commitar.")
        return True

    print(f"\n📤 Publicando no GitHub...")
    print(f"   Commit: {mensagem}")

    # Detectar branch atual
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=REPO_DIR
    )
    branch = branch_result.stdout.strip() or "main"

    cmds = [
        (["git", "add", "-A"],                        "git add"),
        (["git", "commit", "-m", mensagem],            "git commit"),
        (["git", "push", "-u", "origin", branch],      "git push"),
    ]

    for cmd, nome in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_DIR)
        if result.returncode != 0:
            print(f"  ❌ {nome} falhou:")
            print(f"     {result.stderr.strip()}")
            return False
        print(f"  ✓ {nome}")

    print(f"\n✅ GitHub Pages atualizado!")
    print(f"   URL: https://marinhobusiness.github.io/radar-vale-do-aco")
    print(f"   (aguarde 1-2 minutos para propagar)")
    return True


# ── KAGGLE ────────────────────────────────────────────────────────────────────
def publicar_kaggle(caminho_csv=None):
    """
    Publica o dataset CSV no Kaggle.
    Requer: pip install kaggle + credenciais em ~/.kaggle/kaggle.json
    """
    print("\n📦 Publicando dataset no Kaggle...")

    # Verificar se kaggle está instalado
    try:
        import kaggle
    except ImportError:
        print("  ⚠️  kaggle não instalado. Execute: pip install kaggle")
        print("       Depois configure ~/.kaggle/kaggle.json com suas credenciais.")
        return False

    # Verificar credenciais
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print(f"  ⚠️  Credenciais Kaggle não encontradas em {kaggle_json}")
        print("       Baixe em: kaggle.com → Account → API → Create New Token")
        return False

    # Buscar CSV mais recente
    if not caminho_csv:
        csvs = sorted(Path("dados").glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not csvs:
            print("  ❌ Nenhum CSV encontrado em dados/")
            return False
        caminho_csv = str(csvs[0])

    # Criar dataset-metadata.json
    trimestre = f"Q{((date.today().month - 1) // 3) + 1}-{date.today().year}"
    metadata = {
        "title": f"Ipatinga Real Estate Market — Active Listings {trimestre}",
        "id": "marinhobusiness/ipatinga-real-estate-listings",
        "licenses": [{"name": "CC-BY-4.0"}],
        "keywords": [
            "real estate", "brazil", "minas gerais", "ipatinga",
            "vale do aco", "property prices", "data science"
        ],
        "description": (
            f"Active real estate listings scraped from Zap Imóveis, VivaReal, and OLX "
            f"for Ipatinga, Minas Gerais, Brazil. {trimestre}. "
            f"Includes neighborhood, property type, usable area, asking price, "
            f"price per square meter, and collection date. "
            f"Part of the Radar Imobiliário do Vale do Aço project by Wederson Marinho, "
            f"Data Scientist (CRECI-MG 58.263-F · CNAI 51.239 · ORCID: 0009-0004-6401-3465)."
        ),
    }

    dataset_dir = Path("dados") / "kaggle_upload"
    dataset_dir.mkdir(exist_ok=True)

    # Copiar CSV
    shutil.copy(caminho_csv, dataset_dir / "ipatinga_listings.csv")

    # Salvar metadata
    meta_path = dataset_dir / "dataset-metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Upload
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "create", "-p", str(dataset_dir), "--dir-mode", "zip"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  ✓ Dataset publicado no Kaggle")
            print(f"    URL: https://www.kaggle.com/datasets/marinhobusiness/ipatinga-real-estate-listings")
            return True
        else:
            # Tentar update se já existe
            result2 = subprocess.run(
                ["kaggle", "datasets", "version", "-p", str(dataset_dir),
                 "-m", f"Atualização {trimestre}", "--dir-mode", "zip"],
                capture_output=True, text=True
            )
            if result2.returncode == 0:
                print("  ✓ Dataset atualizado no Kaggle (nova versão)")
                return True
            else:
                print(f"  ❌ Kaggle: {result2.stderr.strip()}")
                return False
    except FileNotFoundError:
        print("  ⚠️  kaggle CLI não encontrado. Execute: pip install kaggle")
        return False


# ── ZENODO (instrução manual — API requer token) ──────────────────────────────
def instrucoes_zenodo(caminho_json=None):
    """
    Zenodo não tem CLI oficial fácil. Gera as instruções precisas.
    Para automação futura: usar requests com ZENODO_TOKEN env var.
    """
    if caminho_json:
        with open(caminho_json, "r", encoding="utf-8") as f:
            payload = json.load(f)
        edicao = payload["meta"]["edicao"]
        n      = payload["meta"]["n_total"]
    else:
        edicao = f"Q{((date.today().month - 1) // 3) + 1}/{date.today().year}"
        n      = "?"

    print("\n📚 Zenodo DOI — instruções:")
    print(f"""
  Para registrar o DOI desta edição no Zenodo:

  1. Acesse https://zenodo.org e faça login com ORCID
  2. Clique em "New upload"
  3. Upload dos arquivos:
       - index.html  (dashboard)
       - dados/ipatinga_imoveis_*.csv  (dataset bruto)

  4. Metadados (copie):
     Title:    Radar Imobiliário do Vale do Aço — {edicao}
     Type:     Dataset + Report
     Authors:  Marinho, Wederson (ORCID: 0009-0004-6401-3465)
     Keywords: real estate, ipatinga, vale do aco, data science, FipeZAP
     License:  Creative Commons Attribution 4.0
     n observações: {n}

  5. Após publicar, copie o DOI e adicione ao README.md:
     [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)]
     (https://doi.org/10.5281/zenodo.XXXXXXX)

  6. Execute: python publicar.py --atualizar-readme SEU_DOI
    """)


# ── ATUALIZAR README COM DOI ──────────────────────────────────────────────────
def atualizar_readme_doi(doi):
    """Adiciona o badge de DOI ao README.md."""
    readme = REPO_DIR / "README.md"
    if not readme.exists():
        print("❌ README.md não encontrado")
        return

    conteudo = readme.read_text(encoding="utf-8")
    badge = f"\n[![DOI](https://zenodo.org/badge/DOI/{doi}.svg)](https://doi.org/{doi})\n"

    if doi in conteudo:
        print(f"ℹ️  DOI {doi} já está no README.md")
        return

    # Inserir após o título
    linhas = conteudo.split("\n")
    pos = 1  # após a primeira linha (título)
    linhas.insert(pos, badge)
    readme.write_text("\n".join(linhas), encoding="utf-8")
    print(f"✓ DOI {doi} adicionado ao README.md")

    # Commitar o README atualizado
    subprocess.run(["git", "add", "README.md"], cwd=REPO_DIR)
    subprocess.run(
        ["git", "commit", "-m", f"docs: adiciona DOI Zenodo {doi}"],
        cwd=REPO_DIR
    )
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR)
    print("✓ README.md atualizado e publicado")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def publicar(mensagem=None, kaggle=False, doi=None):
    print("=" * 60)
    print("PUBLICAÇÃO — RADAR IMOBILIÁRIO VALE DO AÇO")
    print("=" * 60)

    # GitHub Pages
    ok = git_push(mensagem)

    # Kaggle (opcional)
    if kaggle:
        publicar_kaggle()
    else:
        print("\n  ℹ️  Kaggle: pulado (use --kaggle para publicar o dataset)")

    # Zenodo
    jsons = sorted(Path("dados").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    instrucoes_zenodo(str(jsons[0]) if jsons else None)

    # Atualizar README com DOI se fornecido
    if doi:
        atualizar_readme_doi(doi)

    return ok


if __name__ == "__main__":
    args = sys.argv[1:]

    # --atualizar-readme DOI
    if "--atualizar-readme" in args:
        idx = args.index("--atualizar-readme")
        doi_arg = args[idx + 1] if idx + 1 < len(args) else None
        if doi_arg:
            atualizar_readme_doi(doi_arg)
        else:
            print("❌ Informe o DOI: python publicar.py --atualizar-readme 10.5281/zenodo.XXXXXXX")
        sys.exit(0)

    kaggle_flag = "--kaggle" in args
    msg = next((a for a in args if not a.startswith("--")), None)

    publicar(mensagem=msg, kaggle=kaggle_flag)
