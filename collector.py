"""
Roda uma coleta de preços contra o catálogo salvo no banco.

Uso:
    python collector.py

Escreve uma linha em `cotacoes` para cada (item, fornecedor) que tiver URL
cadastrada em `urls_produto`. Nunca sobrescreve leituras antigas — cada
coleta é uma linha nova com timestamp, então dá pra auditar preço ao longo
do tempo. A interface e a exportação sempre olham só a leitura mais recente
de cada par (item, fornecedor).
"""
import datetime

from db import conectar
from scrapers.base import ErroColeta
from scrapers import f3d, dfila, lab3d
from validacao import validar_faixa

SCRAPERS = {
    "F3D": f3d.extrair_preco,
    "3DFILA": dfila.extrair_preco,
    "3DLAB": lab3d.extrair_preco,
}


def coletar_tudo():
    conn = conectar()
    cur = conn.cursor()

    linhas = cur.execute("""
        SELECT u.item_id, u.fornecedor_id, u.url, i.especificacao,
               i.faixa_min, i.faixa_max, f.nome AS fornecedor
        FROM urls_produto u
        JOIN itens i ON i.id = u.item_id
        JOIN fornecedores f ON f.id = u.fornecedor_id
        ORDER BY i.ordem, f.id
    """).fetchall()

    if not linhas:
        print("Nenhuma URL cadastrada em urls_produto ainda — rode seed.py "
              "ou cadastre URLs pela interface primeiro.")
        return

    ok = suspeitos = falhas = 0

    for linha in linhas:
        scraper = SCRAPERS.get(linha["fornecedor"])
        if scraper is None:
            print(f"[IGNORADO] sem scraper cadastrado para {linha['fornecedor']}")
            continue

        agora = datetime.datetime.now().isoformat(timespec="seconds")

        try:
            resultado = scraper(linha["url"])
        except ErroColeta as e:
            cur.execute(
                "INSERT INTO cotacoes (item_id, fornecedor_id, preco_unitario, metodo, status, mensagem, coletado_em) "
                "VALUES (?, ?, NULL, 'parser', 'falha', ?, ?)",
                (linha["item_id"], linha["fornecedor_id"], str(e), agora),
            )
            print(f"[FALHA]    {linha['fornecedor']:8s} / {linha['especificacao']}: {e}")
            falhas += 1
            continue

        status_faixa, motivo_faixa = validar_faixa(
            resultado.preco_unitario, linha["faixa_min"], linha["faixa_max"]
        )
        # se o scraper já marcou como suspeito (ex.: sem confirmar variante),
        # isso prevalece mesmo que o preço esteja dentro da faixa
        status_final = "suspeito" if "suspeito" in (resultado.status, status_faixa) else "ok"
        motivo = motivo_faixa or resultado.mensagem

        cur.execute(
            "INSERT INTO cotacoes (item_id, fornecedor_id, preco_unitario, metodo, status, mensagem, coletado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (linha["item_id"], linha["fornecedor_id"], resultado.preco_unitario,
             resultado.metodo, status_final, motivo, agora),
        )

        if status_final == "ok":
            ok += 1
        else:
            suspeitos += 1
        print(f"[{status_final.upper():8s}] {linha['fornecedor']:8s} / "
              f"{linha['especificacao']}: R${resultado.preco_unitario:.2f}"
              + (f"  ({motivo})" if motivo else ""))

    conn.commit()
    conn.close()
    print(f"\nColeta concluída: {ok} ok, {suspeitos} suspeitos, {falhas} falhas.")


if __name__ == "__main__":
    coletar_tudo()
