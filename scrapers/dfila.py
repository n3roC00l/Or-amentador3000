"""
3DFila (3dfila.com.br) roda em WooCommerce (WordPress).

*** VALIDAR ANTES DE CONFIAR EM PRODUÇÃO ***
O preço "em destaque" da página é um preço "a partir de" — da variante MAIS
BARATA do produto (ex.: amostra de 75g), não do carretel de 1,0kg que é o
que a gente compra. Confirmado em 28/07/2026: a página de
"Filamento PLA Amarelo" mostra faixa de R$5,90 a R$89,90 dependendo do peso
escolhido. Usar o preço em destaque sem checar a variante geraria uma
cotação drasticamente errada.

Produtos variáveis do WooCommerce normalmente expõem TODAS as combinações
de variante+preço num atributo `data-product_variations` (JSON) dentro do
formulário de compra. Este parser procura esse bloco e escolhe a variante
de 1kg dentro dele.

Isso NÃO foi validado contra o HTML bruto real do site — o ambiente onde
este código foi escrito não tem acesso de rede a lojas externas, só a
texto renderizado via busca. Antes de rodar isso de verdade:
  1. `pip install requests beautifulsoup4`
  2. Rode este arquivo direto (`python dfila.py <url-de-um-produto>`) e
     confira se o preço bate com o carrinho de verdade.
  3. Se o bloco `data-product_variations` não existir no HTML (alguns temas
     carregam variação só via chamada AJAX separada), este parser falha
     explicitamente — nesse caso o próximo passo é trocar para Playwright
     e simular a seleção da variante no navegador.
"""
import json
import re
from html import unescape

import requests

from .base import HEADERS, ErroColeta, ResultadoColeta

_PADRAO_VARIACOES = re.compile(r'data-product_variations="([^"]+)"')
_PESO_1KG = ("1,0 kg", "1kg", "1 kg", "1,0kg")


def extrair_preco(url: str, peso_alvo: str = "1kg") -> ResultadoColeta:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    html = resp.text

    m = _PADRAO_VARIACOES.search(html)
    if not m:
        raise ErroColeta(
            f"Bloco de variações não encontrado em {url} — o preço em "
            "destaque da página é 'a partir de' e NÃO deve ser usado como "
            "preço do carretel de 1kg. Provável necessidade de Playwright."
        )

    try:
        variacoes = json.loads(unescape(m.group(1)))
    except json.JSONDecodeError as e:
        raise ErroColeta(f"Bloco de variações malformado em {url}: {e}")

    for v in variacoes:
        atributos = " ".join(str(x).lower() for x in v.get("attributes", {}).values())
        if any(p in atributos for p in _PESO_1KG):
            preco = v.get("display_price")
            if preco is None:
                raise ErroColeta(f"Variante de 1kg encontrada mas sem display_price em {url}")
            return ResultadoColeta(preco_unitario=float(preco), metodo="parser", status="ok")

    raise ErroColeta(
        f"Nenhuma variante de 1kg encontrada em {url} — variações disponíveis "
        f"não bateram com {_PESO_1KG}. Confira manualmente o HTML."
    )


if __name__ == "__main__":
    import sys
    resultado = extrair_preco(sys.argv[1])
    print(resultado)
