"""
Scraper Híbrido — Fase 3: seletores em arquivo de configuração + validação dos dados
Lê as regras de coleta do config.json, percorre todas as páginas,
valida cada item e separa os válidos dos rejeitados.

Uso:
    python scraper.py                 (usa o config.json)
    python scraper.py outro_site.json (usa outro arquivo de configuração)
"""

import csv
import json
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (scraper-hibrido; projeto de estudo)"}
TIPOS_VALIDOS = {"texto", "numero", "url", "mapa"}


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def carregar_config(caminho):
    """Lê o arquivo de configuração e confere se tem tudo o que é necessário."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            config = json.load(arquivo)
    except FileNotFoundError:
        raise SystemExit(f"Arquivo de configuração não encontrado: {caminho}")
    except json.JSONDecodeError as erro:
        raise SystemExit(f"Erro no {caminho}, linha {erro.lineno}: {erro.msg}")

    # Confere as chaves obrigatórias antes de começar a coleta
    obrigatorias = {
        "site": ["url_inicial", "arquivo_saida", "arquivo_rejeitados"],
        "coleta": ["max_tentativas", "pausa_entre_paginas"],
        "seletores": ["item", "campos"],
    }
    for secao, chaves in obrigatorias.items():
        if secao not in config:
            raise SystemExit(f"Falta a seção '{secao}' no {caminho}")
        for chave in chaves:
            if chave not in config[secao]:
                raise SystemExit(f"Falta '{chave}' na seção '{secao}' do {caminho}")

    for nome, regra in config["seletores"]["campos"].items():
        if "seletor" not in regra:
            raise SystemExit(f"O campo '{nome}' não tem 'seletor' no {caminho}")
        tipo = regra.get("tipo", "texto")
        if tipo not in TIPOS_VALIDOS:
            raise SystemExit(f"Tipo '{tipo}' do campo '{nome}' não existe. Use: {TIPOS_VALIDOS}")
        if tipo == "mapa" and "mapa" not in regra:
            raise SystemExit(f"O campo '{nome}' é do tipo 'mapa', mas não tem a chave 'mapa'")

    return config


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def baixar_pagina(url, max_tentativas):
    """Baixa a página e devolve o HTML. Tenta de novo em falhas temporárias."""
    for tentativa in range(1, max_tentativas + 1):
        try:
            resposta = requests.get(url, headers=HEADERS, timeout=10)
            resposta.raise_for_status()
            resposta.encoding = "utf-8"
            return resposta.text

        except requests.HTTPError as erro:
            status = erro.response.status_code
            if status < 500:
                raise
            print(f"  Erro {status} no servidor (tentativa {tentativa}/{max_tentativas})")

        except (requests.ConnectionError, requests.Timeout):
            print(f"  Falha de conexão (tentativa {tentativa}/{max_tentativas})")

        if tentativa < max_tentativas:
            espera = 2 ** tentativa
            print(f"  Aguardando {espera}s antes de tentar de novo...")
            time.sleep(espera)

    raise RuntimeError(f"Não foi possível baixar {url} após {max_tentativas} tentativas")


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------

def texto_para_numero(texto):
    """Converte textos como '£51.77', 'R$ 1.234,56' ou '1,234.56' em número."""
    so_numeros = re.sub(r"[^\d,.]", "", texto)  # tira símbolos de moeda e espaços
    if not so_numeros:
        return None

    if "," in so_numeros and "." in so_numeros:
        # O separador que aparece por último é o decimal
        if so_numeros.rfind(",") > so_numeros.rfind("."):
            so_numeros = so_numeros.replace(".", "").replace(",", ".")  # 1.234,56
        else:
            so_numeros = so_numeros.replace(",", "")                    # 1,234.56
    elif "," in so_numeros:
        so_numeros = so_numeros.replace(",", ".")                       # 51,77

    try:
        return float(so_numeros)
    except ValueError:
        return None


def extrair_campo(item, regra, url_pagina):
    """Aplica a regra de um campo ao item. Devolve o valor, ou None se falhar."""
    elemento = item.select_one(regra["seletor"])
    if elemento is None:
        return None  # seletor não encontrou nada: a validação vai acusar

    atributo = regra.get("atributo")
    bruto = elemento.get(atributo) if atributo else elemento.get_text(strip=True)
    if bruto is None or bruto == "" or bruto == []:
        return None

    tipo = regra.get("tipo", "texto")

    if tipo == "mapa":
        # O atributo "class" vem como lista (ex.: ["star-rating", "Three"])
        opcoes = bruto if isinstance(bruto, list) else [bruto]
        for opcao in opcoes:
            if opcao in regra["mapa"]:
                return regra["mapa"][opcao]
        return None

    if isinstance(bruto, list):
        bruto = " ".join(bruto)
    bruto = bruto.strip()

    if tipo == "numero":
        return texto_para_numero(bruto)
    if tipo == "url":
        return urljoin(url_pagina, bruto)
    return bruto or None


def extrair_itens(html, url_pagina, seletores):
    """Encontra todos os itens da página e extrai os campos de cada um."""
    sopa = BeautifulSoup(html, "html.parser")
    itens = []
    for bloco in sopa.select(seletores["item"]):
        registro = {}
        for nome, regra in seletores["campos"].items():
            registro[nome] = extrair_campo(bloco, regra, url_pagina)
        itens.append(registro)
    return itens


def proxima_pagina(html, url_pagina, seletor):
    """Devolve a URL da próxima página, ou None se esta for a última."""
    if not seletor:
        return None  # site sem paginação
    sopa = BeautifulSoup(html, "html.parser")
    botao = sopa.select_one(seletor)
    if botao is None or not botao.get("href"):
        return None
    return urljoin(url_pagina, botao["href"])


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def validar_item(registro, campos):
    """Devolve a lista de problemas do item. Lista vazia = item válido."""
    problemas = []
    for nome, regra in campos.items():
        valor = registro.get(nome)

        if valor is None:
            if regra.get("obrigatorio", False):
                problemas.append(f"{nome} vazio ou não encontrado")
            continue

        tipo = regra.get("tipo", "texto")
        if tipo == "numero" and valor < 0:
            problemas.append(f"{nome} negativo ({valor})")
        if tipo == "url" and not valor.startswith(("http://", "https://")):
            problemas.append(f"{nome} não é um endereço válido ({valor})")

    return problemas


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------

def coletar_tudo(config):
    """Percorre as páginas, separando itens válidos e rejeitados."""
    seletores = config["seletores"]
    coleta = config["coleta"]
    limite = coleta.get("limite_paginas")

    validos, rejeitados = [], []
    url = config["site"]["url_inicial"]
    numero = 1

    while url:
        print(f"Página {numero}: {url}")
        try:
            html = baixar_pagina(url, coleta["max_tentativas"])
        except (requests.RequestException, RuntimeError) as erro:
            print(f"\nColeta interrompida na página {numero}: {erro}")
            break

        itens = extrair_itens(html, url, seletores)
        if not itens:
            print(f"  AVISO: nenhum item encontrado com o seletor '{seletores['item']}'."
                  " O site pode ter mudado o layout.")

        bons_na_pagina = 0
        for registro in itens:
            problemas = validar_item(registro, seletores["campos"])
            if problemas:
                registro["motivo"] = "; ".join(problemas)
                rejeitados.append(registro)
            else:
                validos.append(registro)
                bons_na_pagina += 1

        ruins_na_pagina = len(itens) - bons_na_pagina
        resumo = f"  {bons_na_pagina} válidos"
        if ruins_na_pagina:
            resumo += f", {ruins_na_pagina} rejeitados"
        print(f"{resumo} (total: {len(validos)})")

        if limite and numero >= limite:
            break

        url = proxima_pagina(html, url, seletores.get("proxima_pagina"))
        numero += 1
        if url:
            time.sleep(coleta["pausa_entre_paginas"])

    return validos, rejeitados


def salvar_csv(registros, caminho, colunas):
    """Grava a lista de registros num arquivo CSV."""
    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(registros)


def main():
    caminho_config = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    config = carregar_config(caminho_config)
    site = config["site"]
    colunas = list(config["seletores"]["campos"])  # a ordem das colunas segue o config

    print(f"Coletando: {site.get('nome', site['url_inicial'])}\n")
    validos, rejeitados = coletar_tudo(config)

    print()
    if validos:
        salvar_csv(validos, site["arquivo_saida"], colunas)
        print(f"{len(validos)} itens válidos salvos em {site['arquivo_saida']}")
    else:
        print("Nenhum item válido coletado.")

    if rejeitados:
        salvar_csv(rejeitados, site["arquivo_rejeitados"], colunas + ["motivo"])
        print(f"{len(rejeitados)} itens rejeitados salvos em {site['arquivo_rejeitados']}"
              " (veja a coluna 'motivo')")


if __name__ == "__main__":
    main()