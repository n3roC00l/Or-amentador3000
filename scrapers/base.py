"""
Interface comum a todos os scrapers de fornecedor.

Regra de ouro: um scraper NUNCA devolve preço vazio/zero silenciosamente.
Se não conseguir extrair um preço em que confia, levanta ErroColeta com uma
mensagem explicando o motivo — isso vira uma linha status='falha' no banco,
visível na interface, em vez de virar um 0 silencioso que contamina o total.
"""
from dataclasses import dataclass
from typing import Optional


class ErroColeta(Exception):
    """Falha explícita ao extrair preço de uma página."""


@dataclass
class ResultadoColeta:
    preco_unitario: Optional[float]
    metodo: str       # 'parser' | 'ia'
    status: str = "ok"   # 'ok' | 'suspeito' — 'falha' é tratado via ErroColeta, não aqui
    mensagem: str = ""


HEADERS = {
    # ASCII puro de propósito: caracteres acentuados neste header derrubam a
    # requisição com 403 no WAF (Cloudflare) da 3DLAB — confirmado em
    # 28/07/2026 comparando a mesma URL lado a lado, só variando acento vs
    # sem acento no texto abaixo. 3DFILA e F3D não pareciam se importar, mas
    # o header é compartilhado pelos três, então fica ASCII para todos.
    "User-Agent": (
        "Mozilla/5.0 (compatible; CTP-CotacaoBot/1.0; "
        "+https://cillatechpark.com.br) "
        "coleta de precos para cotacao interna, uso nao comercial"
    )
}
