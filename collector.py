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
import time

import requests

from db import conectar
from scrapers.base import ErroColeta
from scrapers import f3d, dfila, lab3d
from validacao import validar_faixa

SCRAPERS = {
    "F3D": f3d.extrair_preco,
    "3DFILA": dfila.extrair_preco,
    "3DLAB": lab3d.extrair_preco,
}

# 3DLAB tem bloqueio intermitente por rate-limit (Cloudflare) — confirmado em
# 28/07/2026 fazendo a mesma requisição repetidas vezes: rajadas levam a 403
# esporádico que passa sozinho segundos depois. Vale a pena tentar de novo
# antes de desistir; os outros fornecedores não mostraram esse padrão, mas
# não custa aplicar a mesma rede de segurança pra todos.
TENTATIVAS_403 = 2
ESPERA_ENTRE_TENTATIVAS = 2.0


def _extrair_com_retry(scraper, url):
    """
    Além do retry em 403, converte qualquer erro de rede (timeout, conexão
    recusada etc.) em ErroColeta — sem isso, uma falha de rede num único
    produto derrubava a coleta inteira (exceção não tratada), em vez de virar
    só uma linha 'falha' pra aquele item e seguir pros próximos.
    """
    for tentativa in range(TENTATIVAS_403 + 1):
        try:
            return scraper(url)
        except requests.exceptions.HTTPError as e:
            eh_403 = e.response is not None and e.response.status_code == 403
            if not eh_403 or tentativa == TENTATIVAS_403:
                raise ErroColeta(f"HTTP {e.response.status_code if e.response is not None else '?'} em {url}: {e}")
            time.sleep(ESPERA_ENTRE_TENTATIVAS)
        except requests.exceptions.RequestException as e:
            raise ErroColeta(f"erro de rede em {url}: {e}")


def coletar_tudo(progress_callback=None):
    """
    progress_callback(concluidos, total, linha_texto) é chamado depois de
    cada (item, fornecedor) processado, pra quem chamar (ex.: a interface
    Streamlit) poder mostrar progresso ao vivo sem esperar a coleta inteira
    terminar.
    """
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
        conn.close()
        print("Nenhuma URL cadastrada em urls_produto ainda — rode seed.py "
              "ou cadastre URLs pela interface primeiro.")
        return {"ok": 0, "suspeitos": 0, "falhas": 0, "total": 0}

    total = len(linhas)
    ok = suspeitos = falhas = 0

    for indice, linha in enumerate(linhas, start=1):
        scraper = SCRAPERS.get(linha["fornecedor"])
        if scraper is None:
            texto = f"[IGNORADO] sem scraper cadastrado para {linha['fornecedor']}"
            print(texto)
            if progress_callback:
                progress_callback(indice, total, texto)
            continue

        agora = datetime.datetime.now().isoformat(timespec="seconds")

        try:
            resultado = _extrair_com_retry(scraper, linha["url"])
        except ErroColeta as e:
            cur.execute(
                "INSERT INTO cotacoes (item_id, fornecedor_id, preco_unitario, metodo, status, mensagem, coletado_em) "
                "VALUES (?, ?, NULL, 'parser', 'falha', ?, ?)",
                (linha["item_id"], linha["fornecedor_id"], str(e), agora),
            )
            texto = f"[FALHA]    {linha['fornecedor']:8s} / {linha['especificacao']}: {e}"
            print(texto)
            falhas += 1
            if progress_callback:
                progress_callback(indice, total, texto)
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
        texto = (f"[{status_final.upper():8s}] {linha['fornecedor']:8s} / "
                 f"{linha['especificacao']}: R${resultado.preco_unitario:.2f}"
                 + (f"  ({motivo})" if motivo else ""))
        print(texto)
        if progress_callback:
            progress_callback(indice, total, texto)

    conn.commit()
    conn.close()
    resumo = {"ok": ok, "suspeitos": suspeitos, "falhas": falhas, "total": total}
    print(f"\nColeta concluída: {ok} ok, {suspeitos} suspeitos, {falhas} falhas.")
    return resumo


if __name__ == "__main__":
    coletar_tudo()
