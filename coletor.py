"""
coletor.py — Radar Imobiliário do Vale do Aço
Coleta anúncios ativos de apartamentos em Ipatinga-MG
Portais: Zap Imóveis e VivaReal (Grupo OLX)
Autor: Wederson Marinho · Data Scientist
"""

import requests
import json
import csv
import time
import random
import re
import os
from datetime import date
from pathlib import Path

# ── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
CIDADE        = "ipatinga-mg"
TIPO_IMOVEL   = "apartamentos"   # apartamentos | casas | comercial
OPERACAO      = "venda"          # venda | aluguel
MAX_PAGINAS   = 10               # ~250 anúncios por portal
DELAY_MIN     = 2.5              # segundos entre requests (respeitoso)
DELAY_MAX     = 5.0
OUTPUT_DIR    = Path("dados")
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_COLETA   = date.today().isoformat()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.zapimoveis.com.br/",
}

# ── BAIRROS ALVO ──────────────────────────────────────────────────────────────
BAIRROS_ALVO = [
    "Bom Retiro", "Chácaras", "Cidade Nobre", "Bethânia", "Veneza",
    "Horto", "Iguaçu", "Esperança", "Novo Cruzeiro", "Cariru",
    "Caravelas", "Forquilha", "Centro", "Jardim Panorama", "Imbaúbas",
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def esperar():
    """Delay aleatório respeitoso entre requests."""
    t = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"  ⏳ aguardando {t:.1f}s...")
    time.sleep(t)

def limpar_numero(texto):
    """Extrai número de string como 'R$ 450.000' → 450000."""
    if not texto:
        return None
    nums = re.sub(r"[^\d]", "", str(texto))
    return int(nums) if nums else None

def calcular_preco_m2(valor, area):
    """Calcula preço por m² com validação."""
    if not valor or not area or area <= 0:
        return None
    pm2 = round(valor / area)
    # Filtro de sanidade: R$ 2.000 a R$ 25.000/m²
    if pm2 < 2000 or pm2 > 25000:
        return None
    return pm2

def inferir_bairro(titulo, descricao, bairro_raw):
    """Tenta identificar o bairro a partir dos campos disponíveis."""
    texto = f"{titulo} {descricao} {bairro_raw}".upper()
    for b in BAIRROS_ALVO:
        if b.upper() in texto:
            return b
    return bairro_raw.title().strip() if bairro_raw else "Não identificado"

# ── COLETOR ZAP IMÓVEIS (API não-oficial) ─────────────────────────────────────
def coletar_zap(paginas=MAX_PAGINAS):
    """
    Zap Imóveis expõe dados via endpoint JSON interno.
    URL descoberta via DevTools → Network → XHR.
    """
    print("\n📡 Coletando Zap Imóveis...")
    resultados = []

    for pagina in range(1, paginas + 1):
        url = (
            f"https://glue-api.zapimoveis.com.br/v2/listings"
            f"?user=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
            f"&portal=ZAP"
            f"&business=SALE"
            f"&categoryPage=RESULT"
            f"&listingType=USED"
            f"&unitTypes=APARTMENT"
            f"&size=24"
            f"&from={((pagina - 1) * 24)}"
            f"&q=Ipatinga%2C%20MG"
            f"&includeFields=search(result(listings(listing(displayAddressType,amenities,"
            f"usableAreas,constructionStatus,listingType,description,title,unitTypes,"
            f"nonActivationReason,propertyType,unitSubTypes,unitsOnTheFloor,ownershipStatus,"
            f"address,xmlId,publicationType,externalId,bathrooms,usageTypes,totalAreas,"
            f"advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,"
            f"pricingInfos,showPrice,resale,buildings,capacityLimit,status),account("
            f"id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,"
            f"minisite),medias,accountLink,link)),totalCount))"
        )

        hdrs = dict(HEADERS)
        hdrs["x-domain"] = "www.zapimoveis.com.br"

        try:
            resp = requests.get(url, headers=hdrs, timeout=20)
            if resp.status_code != 200:
                print(f"  ⚠️  Zap pág {pagina}: status {resp.status_code}")
                break

            dados = resp.json()
            listings = (
                dados
                .get("search", {})
                .get("result", {})
                .get("listings", [])
            )

            if not listings:
                print(f"  ℹ️  Zap pág {pagina}: sem mais resultados")
                break

            for item in listings:
                lst = item.get("listing", {})
                endereco = lst.get("address", {})
                precos = lst.get("pricingInfos", [{}])

                # Valor de venda
                valor = None
                for p in precos:
                    if p.get("businessType") == "SALE":
                        valor = limpar_numero(p.get("price"))
                        break

                # Área
                areas = lst.get("usableAreas", []) or lst.get("totalAreas", [])
                area = None
                if areas:
                    try:
                        area = float(str(areas[0]).replace(",", "."))
                    except Exception:
                        pass

                preco_m2 = calcular_preco_m2(valor, area)
                if not preco_m2:
                    continue

                bairro_raw = endereco.get("neighborhood", "")
                titulo = lst.get("title", "")
                descricao = lst.get("description", "")

                resultados.append({
                    "bairro": inferir_bairro(titulo, descricao, bairro_raw),
                    "tipo": lst.get("unitTypes", [""])[0] if lst.get("unitTypes") else "",
                    "quartos": (lst.get("bedrooms") or [None])[0],
                    "banheiros": (lst.get("bathrooms") or [None])[0],
                    "area_m2": area,
                    "valor_anunciado": valor,
                    "preco_m2": preco_m2,
                    "logradouro": endereco.get("street", ""),
                    "portal": "Zap Imóveis",
                    "data_coleta": DATA_COLETA,
                    "id_anuncio": lst.get("externalId", ""),
                    "titulo": titulo[:120],
                })

            print(f"  ✓ Zap pág {pagina}: {len(listings)} anúncios | acumulado: {len(resultados)}")
            esperar()

        except requests.RequestException as e:
            print(f"  ❌ Zap pág {pagina}: erro de conexão — {e}")
            esperar()
            continue
        except json.JSONDecodeError:
            print(f"  ❌ Zap pág {pagina}: resposta não é JSON válido")
            break

    return resultados


# ── COLETOR VIVAREAL (API não-oficial) ────────────────────────────────────────
def coletar_vivareal(paginas=MAX_PAGINAS):
    """
    VivaReal usa a mesma infraestrutura do Grupo OLX/Zap.
    Endpoint similar, parâmetro portal=VIVAREAL.
    """
    print("\n📡 Coletando VivaReal...")
    resultados = []

    for pagina in range(1, paginas + 1):
        url = (
            f"https://glue-api.vivareal.com.br/v2/listings"
            f"?user=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
            f"&portal=VIVAREAL"
            f"&business=SALE"
            f"&categoryPage=RESULT"
            f"&unitTypes=APARTMENT"
            f"&size=24"
            f"&from={((pagina - 1) * 24)}"
            f"&q=Ipatinga%2C%20MG"
            f"&includeFields=search(result(listings(listing(displayAddressType,amenities,"
            f"usableAreas,constructionStatus,listingType,description,title,unitTypes,"
            f"address,bathrooms,bedrooms,pricingInfos,showPrice,totalAreas,externalId),"
            f"account(id,name),medias,link)),totalCount))"
        )

        hdrs = dict(HEADERS)
        hdrs["Referer"] = "https://www.vivareal.com.br/"
        hdrs["x-domain"] = "www.vivareal.com.br"

        try:
            resp = requests.get(url, headers=hdrs, timeout=20)
            if resp.status_code != 200:
                print(f"  ⚠️  VivaReal pág {pagina}: status {resp.status_code}")
                break

            dados = resp.json()
            listings = (
                dados
                .get("search", {})
                .get("result", {})
                .get("listings", [])
            )

            if not listings:
                print(f"  ℹ️  VivaReal pág {pagina}: sem mais resultados")
                break

            for item in listings:
                lst = item.get("listing", {})
                endereco = lst.get("address", {})
                precos = lst.get("pricingInfos", [{}])

                valor = None
                for p in precos:
                    if p.get("businessType") == "SALE":
                        valor = limpar_numero(p.get("price"))
                        break

                areas = lst.get("usableAreas", []) or lst.get("totalAreas", [])
                area = None
                if areas:
                    try:
                        area = float(str(areas[0]).replace(",", "."))
                    except Exception:
                        pass

                preco_m2 = calcular_preco_m2(valor, area)
                if not preco_m2:
                    continue

                bairro_raw = endereco.get("neighborhood", "")
                titulo = lst.get("title", "")
                descricao = lst.get("description", "")

                resultados.append({
                    "bairro": inferir_bairro(titulo, descricao, bairro_raw),
                    "tipo": lst.get("unitTypes", [""])[0] if lst.get("unitTypes") else "",
                    "quartos": (lst.get("bedrooms") or [None])[0],
                    "banheiros": (lst.get("bathrooms") or [None])[0],
                    "area_m2": area,
                    "valor_anunciado": valor,
                    "preco_m2": preco_m2,
                    "logradouro": endereco.get("street", ""),
                    "portal": "VivaReal",
                    "data_coleta": DATA_COLETA,
                    "id_anuncio": lst.get("externalId", ""),
                    "titulo": titulo[:120],
                })

            print(f"  ✓ VivaReal pág {pagina}: {len(listings)} anúncios | acumulado: {len(resultados)}")
            esperar()

        except requests.RequestException as e:
            print(f"  ❌ VivaReal pág {pagina}: erro de conexão — {e}")
            esperar()
            continue
        except json.JSONDecodeError:
            print(f"  ❌ VivaReal pág {pagina}: resposta não é JSON válido")
            break

    return resultados


# ── COLETOR OLX (fallback via API de busca) ───────────────────────────────────
def coletar_olx(paginas=5):
    """
    OLX como fonte complementar para imóveis não listados nos outros portais.
    Usa endpoint de busca com filtros de categoria imobiliária.
    """
    print("\n📡 Coletando OLX (complementar)...")
    resultados = []

    for pagina in range(1, paginas + 1):
        url = (
            f"https://www.olx.com.br/api/ad-search/v2/search"
            f"?q=apartamento+ipatinga"
            f"&cat=1020"                # categoria: imóveis
            f"&sf=1"                    # somente venda
            f"&o={pagina}"
            f"&uq=ipatinga-mg"
        )

        hdrs = dict(HEADERS)
        hdrs["Referer"] = "https://www.olx.com.br/"

        try:
            resp = requests.get(url, headers=hdrs, timeout=20)
            if resp.status_code != 200:
                print(f"  ⚠️  OLX pág {pagina}: status {resp.status_code}")
                break

            dados = resp.json()
            anuncios = dados.get("ads", [])

            if not anuncios:
                print(f"  ℹ️  OLX pág {pagina}: sem mais resultados")
                break

            for ad in anuncios:
                preco_str = ad.get("price", "")
                valor = limpar_numero(preco_str)

                # Área — OLX armazena em propriedades customizadas
                area = None
                for prop in ad.get("properties", []):
                    if prop.get("name") in ("size", "area_size"):
                        try:
                            area = float(str(prop.get("value", "")).replace(",", "."))
                        except Exception:
                            pass

                preco_m2 = calcular_preco_m2(valor, area)
                if not preco_m2:
                    continue

                localizacao = ad.get("location", {})
                bairro_raw = localizacao.get("neighbourhood", "")
                titulo = ad.get("title", "")

                resultados.append({
                    "bairro": inferir_bairro(titulo, "", bairro_raw),
                    "tipo": "APARTMENT",
                    "quartos": None,
                    "banheiros": None,
                    "area_m2": area,
                    "valor_anunciado": valor,
                    "preco_m2": preco_m2,
                    "logradouro": localizacao.get("address", ""),
                    "portal": "OLX",
                    "data_coleta": DATA_COLETA,
                    "id_anuncio": str(ad.get("listId", "")),
                    "titulo": titulo[:120],
                })

            print(f"  ✓ OLX pág {pagina}: {len(anuncios)} anúncios | acumulado: {len(resultados)}")
            esperar()

        except requests.RequestException as e:
            print(f"  ❌ OLX pág {pagina}: erro de conexão — {e}")
            esperar()
            continue
        except json.JSONDecodeError:
            print(f"  ❌ OLX pág {pagina}: resposta não é JSON válido")
            break

    return resultados


# ── DEDUPLICAÇÃO ──────────────────────────────────────────────────────────────
def deduplicar(registros):
    """
    Remove duplicatas cruzadas entre portais.
    Critério: mesmo bairro + mesma área + mesmo valor (tolerância 2%)
    """
    vistos = set()
    limpos = []
    for r in registros:
        # Chave de deduplicação: bairro + quartos + área arredondada + valor arredondado
        area_key = round(r["area_m2"] / 5) * 5 if r["area_m2"] else 0
        val_key  = round(r["valor_anunciado"] / 5000) * 5000 if r["valor_anunciado"] else 0
        chave = (r["bairro"], r.get("quartos"), area_key, val_key)
        if chave not in vistos:
            vistos.add(chave)
            limpos.append(r)
    return limpos


# ── SALVAR CSV ────────────────────────────────────────────────────────────────
def salvar_csv(registros, nome_arquivo=None):
    """Salva os registros em CSV com metadados no nome do arquivo."""
    if not nome_arquivo:
        trimestre = f"Q{((date.today().month - 1) // 3) + 1}"
        ano = date.today().year
        nome_arquivo = OUTPUT_DIR / f"ipatinga_imoveis_{trimestre}_{ano}.csv"

    campos = [
        "bairro", "tipo", "quartos", "banheiros",
        "area_m2", "valor_anunciado", "preco_m2",
        "logradouro", "portal", "data_coleta",
        "id_anuncio", "titulo"
    ]

    with open(nome_arquivo, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(registros)

    print(f"\n✅ CSV salvo: {nome_arquivo} ({len(registros)} registros)")
    return nome_arquivo


# ── MAIN ──────────────────────────────────────────────────────────────────────
def coletar_tudo(paginas_por_portal=MAX_PAGINAS):
    """Pipeline completo de coleta."""
    print("=" * 60)
    print("RADAR IMOBILIÁRIO · VALE DO AÇO")
    print(f"Coleta iniciada: {DATA_COLETA}")
    print("=" * 60)

    todos = []

    # Coleta Zap
    zap = coletar_zap(paginas=paginas_por_portal)
    todos.extend(zap)

    # Coleta VivaReal
    vr = coletar_vivareal(paginas=paginas_por_portal)
    todos.extend(vr)

    # Coleta OLX (complementar, menos páginas)
    olx = coletar_olx(paginas=min(5, paginas_por_portal))
    todos.extend(olx)

    print(f"\n📊 Total bruto: {len(todos)} registros")

    # Deduplicar
    limpos = deduplicar(todos)
    descartados = len(todos) - len(limpos)
    print(f"🔧 Deduplicação: {descartados} duplicatas removidas")
    print(f"✅ Total final: {len(limpos)} registros únicos")

    # Salvar
    caminho = salvar_csv(limpos)

    return limpos, caminho


if __name__ == "__main__":
    dados, arquivo = coletar_tudo()
    print(f"\nPróximo passo: python analisar.py {arquivo}")
