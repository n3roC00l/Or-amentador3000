"""
F3D (filamentos3dbrasil.com.br) roda em Nuvemshop (Tiendanube).

A plataforma injeta o preço do produto direto numa meta tag própria da
página, fora de qualquer ambiguidade de variante ou parcelamento:

    <meta property="nuvemshop:price" content="99.90">

Confirmado inspecionando a página de produto real (28/07/2026). É o
fornecedor mais simples e mais confiável dos três — não precisa de
navegador headless, não tem variante de peso (o produto já é vendido
fechado em 1kg), e o valor bate com o formato que o financeiro já usa
("à vista").
"""
import re

import requests

from .base import HEADERS, ErroColeta, ResultadoColeta

_PADRAO_PRECO = re.compile(r'property="nuvemshop:price"\s+content="([\d.]+)"')
_PADRAO_ESTOQUE = re.compile(r'property="nuvemshop:stock"\s+content="([\d]+)"')


def extrair_preco(url: str) -> ResultadoColeta:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    m = _PADRAO_PRECO.search(resp.text)
    if not m:
        raise ErroColeta(f"meta 'nuvemshop:price' não encontrada em {url}")

    preco = float(m.group(1))

    m_estoque = _PADRAO_ESTOQUE.search(resp.text)
    if m_estoque and m_estoque.group(1) == "0":
        return ResultadoColeta(
            preco_unitario=preco, metodo="parser", status="suspeito",
            mensagem="Produto sinalizado como sem estoque (nuvemshop:stock=0).",
        )

    return ResultadoColeta(preco_unitario=preco, metodo="parser", status="ok")
