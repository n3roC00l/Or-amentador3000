"""
3D Lab (3dlab.com.br) também roda em WooCommerce — mesmo risco de variante
de peso (1kg vs 500g) do 3dfila.py, mesma ressalva de validação se aplica.

*** LIMITAÇÃO CONHECIDA, SEM SOLUÇÃO AUTOMÁTICA NESTA VERSÃO ***
A 3D Lab aplica desconto por volume que soma a quantidade de TODAS as cores
da mesma categoria (ex.: todos os "PLA Premium") dentro do carrinho — não
dá pra saber esse valor olhando um produto isolado, fora de um carrinho de
verdade. Confirmado em 28/07/2026 na página de "PLA Premium Azul Horizonte":
tabela de desconto por quantidade de 3 a 100+ unidades, com nota explícita
"Quantidade considera todos os produtos da mesma categoria no carrinho".

Este parser captura o preço unitário "à vista no pix" SEM desconto de
volume — é uma aproximação deliberada, não um bug escondido. Se o pedido
cruzar os limites de quantidade da tabela, o valor real será menor que o
capturado aqui. Por isso ele nunca marca como 'ok' quando cai no caminho
de fallback por regex (só quando confirma a variante de 1kg via bloco de
variações) — fica 'suspeito' até alguém revisar contra o carrinho real.

Mesma ressalva do dfila.py: não testado contra o HTML bruto real (sem
acesso de rede a lojas externas neste ambiente). Validar antes de produção.
"""
import json
import re
from html import unescape

import requests

from .base import HEADERS, ErroColeta, ResultadoColeta

_PADRAO_VARIACOES = re.compile(r'data-product_variations="([^"]+)"')
_PADRAO_PIX_FALLBACK = re.compile(
    r'R\$\s?([\d.,]+)\s*[àa]\s*vista\s*no\s*pix', re.IGNORECASE
)
_PESO_1KG = ("1kg", "1,0 kg", "1 kg")


def extrair_preco(url: str) -> ResultadoColeta:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    html = resp.text

    m = _PADRAO_VARIACOES.search(html)
    if m:
        try:
            variacoes = json.loads(unescape(m.group(1)))
        except json.JSONDecodeError as e:
            raise ErroColeta(f"Bloco de variações malformado em {url}: {e}")

        for v in variacoes:
            atributos = " ".join(str(x).lower() for x in v.get("attributes", {}).values())
            if any(p in atributos for p in _PESO_1KG):
                preco = v.get("display_price")
                if preco is not None:
                    return ResultadoColeta(
                        preco_unitario=float(preco), metodo="parser", status="suspeito",
                        mensagem="Preço unitário sem desconto por volume (ver aviso no topo do arquivo).",
                    )

    # Fallback: sem bloco de variações reconhecível, tenta ler o preço PIX
    # direto do texto renderizado. Menos confiável — status sempre 'suspeito'.
    m_pix = _PADRAO_PIX_FALLBACK.search(html)
    if not m_pix:
        raise ErroColeta(f"Preço não encontrado em {url} (nem variação, nem PIX no texto).")

    preco = float(m_pix.group(1).replace(".", "").replace(",", "."))
    return ResultadoColeta(
        preco_unitario=preco, metodo="parser", status="suspeito",
        mensagem="Sem confirmação de variante 1kg + sem desconto por volume — validar manualmente.",
    )


if __name__ == "__main__":
    import sys
    resultado = extrair_preco(sys.argv[1])
    print(resultado)
