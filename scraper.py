"""
Scraper Híbrido — Fase 2: paginação + tratamento de erros + retentativas
Percorre todas as páginas de books.toscrape.com e exporta os livros para CSV.
Campos: título, preço, disponibilidade, nota e link.
"""

import csv
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://books.toscrape.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (scraper-hibrido; projeto de estudo)"}
ARQUIVO_SAIDA = "livros.csv"

MAX_TENTATIVAS = 3        # quantas vezes tentar baixar uma página antes de desistir
PAUSA_ENTRE_PAGINAS = 1   # segundos de espera entre páginas, para não sobrecarregar o site
LIMITE_PAGINAS = None    # None = todas; coloque 2 ou 3 para testar mais rápido

# O site indica a nota pela classe CSS ("star-rating Three"), não por número
NOTAS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def baixar_pagina(url):
    """Baixa a página e devolve o HTML. Tenta de novo em falhas temporárias."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resposta = requests.get(url, headers=HEADERS, timeout=10)
            resposta.raise_for_status()
            resposta.encoding = "utf-8"  # evita que "£" vire "Â£"
            return resposta.text

        except requests.HTTPError as erro:
            status = erro.response.status_code
            # Erros 4xx (ex.: 404) não melhoram tentando de novo: desiste na hora
            if status < 500:
                raise
            print(f"  Erro {status} no servidor (tentativa {tentativa}/{MAX_TENTATIVAS})")

        except (requests.ConnectionError, requests.Timeout):
            print(f"  Falha de conexão (tentativa {tentativa}/{MAX_TENTATIVAS})")

        if tentativa < MAX_TENTATIVAS:
            espera = 2 ** tentativa  # 2s, 4s... cada nova tentativa espera mais
            print(f"  Aguardando {espera}s antes de tentar de novo...")
            time.sleep(espera)

    raise RuntimeError(f"Não foi possível baixar {url} após {MAX_TENTATIVAS} tentativas")


def extrair_livros(html, url_pagina):
    """Recebe o HTML e a URL da página; devolve a lista de livros."""
    sopa = BeautifulSoup(html, "html.parser")
    livros = []

    for card in sopa.select("article.product_pod"):
        titulo = card.select_one("h3 a")["title"]

        href = card.select_one("h3 a")["href"]
        link = urljoin(url_pagina, href)  # relativo à página atual, não à inicial

        preco_texto = card.select_one("p.price_color").get_text(strip=True)
        preco = float(preco_texto.replace("£", ""))

        disponibilidade = card.select_one("p.availability").get_text(strip=True)

        classes = card.select_one("p.star-rating")["class"]  # ex.: ["star-rating", "Three"]
        nota = NOTAS.get(classes[1])

        livros.append({
            "titulo": titulo,
            "preco": preco,
            "disponibilidade": disponibilidade,
            "nota": nota,
            "link": link,
        })

    return livros


def proxima_pagina(html, url_pagina):
    """Devolve a URL da próxima página, ou None se esta for a última."""
    sopa = BeautifulSoup(html, "html.parser")
    botao = sopa.select_one("li.next a")
    if botao is None:
        return None
    return urljoin(url_pagina, botao["href"])


def coletar_tudo(url_inicial):
    """Percorre as páginas uma a uma, juntando os livros de todas."""
    todos = []
    url = url_inicial
    numero = 1

    while url:
        print(f"Página {numero}: {url}")
        try:
            html = baixar_pagina(url)
        except (requests.RequestException, RuntimeError) as erro:
            # Para a coleta, mas devolve o que já foi juntado
            print(f"\nColeta interrompida na página {numero}: {erro}")
            break

        livros = extrair_livros(html, url)
        todos.extend(livros)
        print(f"  {len(livros)} livros (total: {len(todos)})")

        if LIMITE_PAGINAS and numero >= LIMITE_PAGINAS:
            break

        url = proxima_pagina(html, url)
        numero += 1
        if url:
            time.sleep(PAUSA_ENTRE_PAGINAS)

    return todos


def salvar_csv(livros, caminho):
    """Grava a lista de livros num arquivo CSV."""
    colunas = ["titulo", "preco", "disponibilidade", "nota", "link"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(livros)


def main():
    livros = coletar_tudo(URL)

    if livros:
        salvar_csv(livros, ARQUIVO_SAIDA)
        print(f"\n{len(livros)} livros salvos em {ARQUIVO_SAIDA}")
    else:
        print("\nNenhum livro coletado.")


if __name__ == "__main__":
    main()