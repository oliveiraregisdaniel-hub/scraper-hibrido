# 🕷️ Scraper Híbrido

> Coleta de dados web que não quebra em silêncio: seletores fazem o trabalho do dia a dia, e a IA entra como plano B só quando o site muda.

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.x-blue?logo=python&logoColor=white)
![Fases](https://img.shields.io/badge/fases-3%2F8%20conclu%C3%ADdas-lightgrey)

---

## 💡 Por que híbrido?

Scrapers tradicionais são **rápidos e baratos**, mas quebram quando o site muda o layout.
Scrapers com IA são **resistentes a mudanças**, mas custam mais e podem errar.

Este projeto combina os dois: a coleta normal usa seletores, e a IA só é acionada quando um seletor falha, com validação do que ela devolve. O resultado é o custo baixo do tradicional com a resistência da IA.

---

## ✅ O que já funciona

- Coleta de título, preço, disponibilidade, nota e link de cada produto
- Navegação automática por todas as páginas (testado com 50 páginas / 1000 itens)
- Retentativas com espera progressiva em falhas de conexão
- Para com segurança em erros graves, salvando o que já foi coletado
- Exportação para CSV compatível com Excel
- **Seletores em arquivo de configuração:** adaptar para outro site é editar o `config.json`, sem mexer no código
- **Validação de cada item:** campos obrigatórios, números e links são conferidos antes de salvar
- **Nada é descartado em silêncio:** itens com problema vão para `rejeitados.csv` com o motivo
- Leitura de preços em vários formatos (`£51.77`, `R$ 1.234,56`, `1,234.56`)

## 🚧 Em desenvolvimento

- Banco SQLite com histórico e comparação entre coletas
- Logs e alerta quando o site muda
- Testes automatizados
- Fallback com IA

📍 Veja o andamento completo no **[Roadmap](ROADMAP.md)**.

---

## ▶️ Como usar

**Requisitos:** Python 3.10 ou superior.

```bash
# 1. Clonar o repositório
git clone https://github.com/oliveiraregisdaniel-hub/scraper-hibrido.git
cd scraper-hibrido

# 2. Instalar as dependências
pip install requests beautifulsoup4

# 3. Rodar
python scraper.py
```

O resultado é salvo em `livros.csv`, e os itens com problema em `rejeitados.csv`.

Para usar outra configuração (por exemplo, outro site):

```bash
python scraper.py outro_site.json
```

**Exemplo de saída no terminal:**

```
Coletando: Books to Scrape

Página 1: https://books.toscrape.com/
  20 válidos (total: 20)
Página 2: https://books.toscrape.com/catalogue/page-2.html
  Falha de conexão (tentativa 1/3)
  Aguardando 2s antes de tentar de novo...
  20 válidos (total: 40)
...
1000 itens válidos salvos em livros.csv
```

---

## ⚙️ Configuração

Tudo o que muda de um site para outro fica no `config.json`:

```json
"preco": {
  "seletor": "p.price_color",
  "tipo": "numero",
  "obrigatorio": true
}
```

| Chave | Para que serve |
|---|---|
| `seletor` | Onde o dado está na página (seletor CSS) |
| `atributo` | Opcional: ler um atributo (`href`, `title`...) em vez do texto |
| `tipo` | `texto`, `numero`, `url` ou `mapa` (tradução por tabela, ex.: `"Three"` → `3`) |
| `obrigatorio` | Se `true`, o item é rejeitado quando esse campo falta |

---

## 🧰 Tecnologias

`Python` · `requests` · `BeautifulSoup`

---

## ⚖️ Uso responsável

O site usado como exemplo, [books.toscrape.com](https://books.toscrape.com), foi criado especificamente para prática de scraping. O scraper respeita uma pausa entre páginas para não sobrecarregar o servidor. Antes de usar em outros sites, verifique os termos de uso e o `robots.txt`.