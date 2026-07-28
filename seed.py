"""
Popula o banco com o catálogo extraído do seu Excel atual
(FILAMENTOS_27072026_-_Mapa_de_Cotação.xlsx).

URLs de 3DLAB e F3D descobertas em 28/07/2026 varrendo o catálogo público
de cada loja (páginas /loja/ do 3DLAB, paginação ?page=N do F3D) e
confirmando cada URL candidata com HTTP 200 antes de cadastrar. A maioria é
correspondência exata de cor. Onde a loja não vende a cor exata do
catálogo original, as fotos de produto das 3 lojas foram comparadas lado a
lado (28/07/2026) para validar a aproximação:
  - PLA Azul/Verde "(CTP)": o "(CTP)" no nome não bate com nenhum atributo
    encontrado nas 3 lojas (provável nota interna da Cilla Tech Park, não
    um atributo do produto) — tratado como PLA Azul/Verde comum. Fotos
    conferem: mesmo tom de azul/verde nas 3 lojas.
  - 3DLAB PLA Rosa: usa "Rosa Pop Art" (rosa vivo/magenta) — bate com a
    foto do 3DFILA e do F3D. **Cuidado:** a URL óbvia pelo slug seria
    "filamento-pla-rosa-bebe", mas essa é foto de rosa bebê pálido (o
    produto foi renomeado para "Rosa Blush", a URL antiga ficou); não usar.
  - 3DLAB PETG Azul/Laranja/Verde: só existem na linha "UV translúcido" —
    fotos conferidas lado a lado com 3DFILA/F3D, mesmo tom de cor nas 3
    lojas. Ainda vale reconferir na prática porque "translúcido" pode se
    comportar diferente ao imprimir (deixa passar mais luz) mesmo com a
    cor batendo na foto do carretel.
  - F3D PETG Laranja: só existe como "laranja painel elétrico" (laranja de
    segurança) — foto conferida, mesmo tom de laranja que 3DFILA/3DLAB.

Sem URL, o coletor não tenta aquele fornecedor pra aquele item (não existe
fallback de "adivinhar o produto").

Faixas de preço (faixa_min/faixa_max) recalibradas em 28/07/2026 com base
nos preços reais coletados nas 3 lojas (ver `cotacoes`), não mais nos
valores do Excel antigo. Faixa = observado ±(20-25%) de margem — larga o
bastante pra não acusar promoção/reajuste normal, justa o bastante pra
pegar erro de parser de verdade (ex.: capturar a variante de amostra em
vez do carretel de 1kg):
  - PLA: observado R$89,90–R$99,90 nas 3 lojas → faixa 65–120
  - PETG: observado R$89,90–R$146,49 (o teto é a linha "UV translúcido" do
    3DLAB, mais cara de propósito, não erro) → faixa 70–170
  - ABS: observado R$74,90–R$99,90 → faixa 55–120
"""
from db import conectar, inicializar

FORNECEDORES = [
    # nome, site, condicao_pagamento, prazo_entrega, frete
    ("3DFILA", "https://3dfila.com.br/", "à vista", "15 dias", 67.4),
    ("3DLAB", "https://3dlab.com.br/", "à vista", "15 dias", 67.4),
    ("F3D", "https://www.filamentos3dbrasil.com.br/", "à vista", "15 dias", 67.4),
]

FAIXA_PLA = (65, 120)
FAIXA_PETG = (70, 170)
FAIXA_ABS = (55, 120)

# especificacao, quantidade, categoria, faixa, url_3dfila, url_3dlab, url_f3d
ITENS = [
    ("PLA Amarelo", 3, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-amarelo/",
     "https://3dlab.com.br/produto/filamento-pla-amarelo/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-amarelo/"),
    ("PLA Azul (CTP)", 5, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-azul-cobalto-175mm/",
     "https://3dlab.com.br/produto/filamento-pla-azul/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-azul/"),
    ("PLA Verde (CTP)", 5, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-verde/",
     "https://3dlab.com.br/produto/filamento-pla-verde/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-verde/"),
    ("PLA Vermelho", 3, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-vermelho/",
     "https://3dlab.com.br/produto/filamento-pla-vermelho/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-vermelho/"),
    ("PLA Laranja", 2, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-laranja/",
     "https://3dlab.com.br/produto/filamento-pla-laranja/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-laranja/"),
    ("PLA Lilás", 2, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-lilas-175mm/",
     "https://3dlab.com.br/produto/filamento-pla-lilas/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-lilas/"),
    ("PLA Rosa", 2, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-rosa/",
     "https://3dlab.com.br/produto/filamento-pla-rosa-pop/",  # aprox. — "Rosa Pop Art", bate com foto do 3DFILA/F3D
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-rosa/"),
    ("PLA Marrom", 2, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-marrom-chocolate-175mm/",
     "https://3dlab.com.br/produto/filamento-pla-marrom/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-marrom/"),
    ("PLA Preto", 5, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-preto/",
     "https://3dlab.com.br/produto/filamento-pla-preto/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-preto/"),
    ("PLA Branco", 5, "PLA", FAIXA_PLA,
     "https://3dfila.com.br/produto/filamento-pla-branco/",
     "https://3dlab.com.br/produto/filamento-pla-branco/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-pla-premium-branco/"),
    ("PETG Azul", 3, "PETG", FAIXA_PETG,
     "https://3dfila.com.br/produto/filamento-petg-xt-azul-caneta-175mm/",
     "https://3dlab.com.br/produto/filamento-petg-uv-azul-translucido-3d-lab/",  # aprox. — linha UV translúcida
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-petg-azul/"),
    ("PETG Preto", 5, "PETG", FAIXA_PETG,
     "https://3dfila.com.br/produto/filamento-petg-preto/",
     "https://3dlab.com.br/produto/filamento-petg-preto/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-petg-preto/"),
    ("PETG Branco", 5, "PETG", FAIXA_PETG,
     "https://3dfila.com.br/produto/filamento-petg-branco/",
     "https://3dlab.com.br/produto/filamento-petg-branco/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-petg-branco/"),
    ("PETG Laranja", 2, "PETG", FAIXA_PETG,
     "https://3dfila.com.br/produto/filamento-petg-xt-laranja-175mm/",
     "https://3dlab.com.br/produto/filamento-petg-uv-laranja-translucido/",  # aprox. — linha UV translúcida
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-petg-laranja-painel-eletrico/"),  # aprox. — laranja de segurança
    ("PETG Verde", 2, "PETG", FAIXA_PETG,
     "https://3dfila.com.br/produto/filamento-petg-xt-verde-175mm/",
     "https://3dlab.com.br/produto/filamento-petg-uv-verde-translucido/",  # aprox. — linha UV translúcida
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-petg-verde/"),
    ("ABS Preto", 3, "ABS", FAIXA_ABS,
     "https://3dfila.com.br/produto/filamento-abs-preto-sepia-premium-175mm/",
     "https://3dlab.com.br/produto/filamento-abs-premium-preto/",
     "https://www.filamentos3dbrasil.com.br/produtos/filamento-abs-premium-preto/"),
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

    for ordem, (spec, qtd, categoria, faixa, url_3dfila, url_3dlab, url_f3d) in enumerate(ITENS, start=1):
        fmin, fmax = faixa
        cur.execute(
            "INSERT OR IGNORE INTO itens (id, ordem, especificacao, quantidade, unidade, categoria, faixa_min, faixa_max) "
            "VALUES (?, ?, ?, ?, 'UN', ?, ?, ?)",
            (ordem, ordem, spec, qtd, categoria, fmin, fmax),
        )
        # o item já pode existir de uma seed anterior (INSERT OR IGNORE não
        # atualiza) — sincroniza a faixa mesmo assim, sem tocar em
        # quantidade (editável pela interface) nem no histórico de cotações
        cur.execute(
            "UPDATE itens SET faixa_min = ?, faixa_max = ? WHERE id = ?",
            (fmin, fmax, ordem),
        )
        for nome_fornecedor, url in (("3DFILA", url_3dfila), ("3DLAB", url_3dlab), ("F3D", url_f3d)):
            cur.execute(
                "INSERT OR IGNORE INTO urls_produto (item_id, fornecedor_id, url) VALUES (?, ?, ?)",
                (ordem, fornecedor_id[nome_fornecedor], url),
            )

    conn.commit()
    conn.close()
    print(f"Seed ok: {len(FORNECEDORES)} fornecedores, {len(ITENS)} itens, "
          f"{len(ITENS) * len(FORNECEDORES)} URLs cadastradas (3DFILA + 3DLAB + F3D).")


if __name__ == "__main__":
    seed()
