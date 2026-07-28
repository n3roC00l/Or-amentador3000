"""
Popula o banco com o catálogo extraído do seu Excel atual
(FILAMENTOS_27072026_-_Mapa_de_Cotação.xlsx).

IMPORTANTE: só o 3DFILA tinha URL por item no arquivo original (coluna N).
3DLAB e F3D só tinham o link da home da loja — então saem sem URL de
produto cadastrada. Sem URL, o coletor não tenta esses dois fornecedores
pra aquele item (não existe fallback de "adivinhar o produto"). Preencha
manualmente em `urls_produto`, ou peça ajuda para descobrir + confirmar as
URLs certas antes de rodar a coleta pra valer.

Faixas de preço (faixa_min/faixa_max) são um ponto de partida, calibrado
pelos valores que já apareciam no seu arquivo — ajuste conforme o
histórico real for aparecendo.
"""
from db import conectar, inicializar

FORNECEDORES = [
    # nome, site, condicao_pagamento, prazo_entrega, frete
    ("3DFILA", "https://3dfila.com.br/", "à vista", "15 dias", 67.4),
    ("3DLAB", "https://3dlab.com.br/", "à vista", "15 dias", 67.4),
    ("F3D", "https://www.filamentos3dbrasil.com.br/", "à vista", "15 dias", 67.4),
]

# especificacao, quantidade, categoria, faixa_min, faixa_max, url_3dfila
ITENS = [
    ("PLA Amarelo", 3, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-amarelo/"),
    ("PLA Azul (CTP)", 5, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-azul-cobalto-175mm/"),
    ("PLA Verde (CTP)", 5, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-verde/"),
    ("PLA Vermelho", 3, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-vermelho/"),
    ("PLA Laranja", 2, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-laranja/"),
    ("PLA Lilás", 2, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-lilas-175mm/"),
    ("PLA Rosa", 2, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-rosa/"),
    ("PLA Marrom", 2, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-marrom-chocolate-175mm/"),
    ("PLA Preto", 5, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-preto/"),
    ("PLA Branco", 5, "PLA", 60, 150, "https://3dfila.com.br/produto/filamento-pla-branco/"),
    ("PETG Azul", 3, "PETG", 70, 180, "https://3dfila.com.br/produto/filamento-petg-xt-azul-caneta-175mm/"),
    ("PETG Preto", 5, "PETG", 70, 180, "https://3dfila.com.br/produto/filamento-petg-preto/"),
    ("PETG Branco", 5, "PETG", 70, 180, "https://3dfila.com.br/produto/filamento-petg-branco/"),
    ("PETG Laranja", 2, "PETG", 70, 180, "https://3dfila.com.br/produto/filamento-petg-xt-laranja-175mm/"),
    ("PETG Verde", 2, "PETG", 70, 180, "https://3dfila.com.br/produto/filamento-petg-xt-verde-175mm/"),
    ("ABS Preto", 3, "ABS", 60, 160, "https://3dfila.com.br/produto/filamento-abs-preto-sepia-premium-175mm/"),
]


def seed():
    inicializar()
    conn = conectar()
    cur = conn.cursor()

    fornecedor_id = {}
    for ordem, (nome, site, cond, prazo, frete) in enumerate(FORNECEDORES, start=1):
        cur.execute(
            "INSERT OR IGNORE INTO fornecedores (id, nome, site, condicao_pagamento, prazo_entrega, frete) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ordem, nome, site, cond, prazo, frete),
        )
        fornecedor_id[nome] = ordem

    for ordem, (spec, qtd, categoria, fmin, fmax, url_3dfila) in enumerate(ITENS, start=1):
        cur.execute(
            "INSERT OR IGNORE INTO itens (id, ordem, especificacao, quantidade, unidade, categoria, faixa_min, faixa_max) "
            "VALUES (?, ?, ?, ?, 'UN', ?, ?, ?)",
            (ordem, ordem, spec, qtd, categoria, fmin, fmax),
        )
        cur.execute(
            "INSERT OR IGNORE INTO urls_produto (item_id, fornecedor_id, url) VALUES (?, ?, ?)",
            (ordem, fornecedor_id["3DFILA"], url_3dfila),
        )

    conn.commit()
    conn.close()
    print(f"Seed ok: {len(FORNECEDORES)} fornecedores, {len(ITENS)} itens, "
          f"{len(ITENS)} URLs (só 3DFILA — completar 3DLAB e F3D manualmente).")


if __name__ == "__main__":
    seed()
