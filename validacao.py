"""Validação de faixa plausível — nunca descarta uma leitura, só sinaliza."""
from typing import Optional, Tuple


def validar_faixa(
    preco: Optional[float], faixa_min: Optional[float], faixa_max: Optional[float]
) -> Tuple[str, Optional[str]]:
    """
    Retorna (status, motivo).
    status é 'ok' ou 'suspeito' — a decisão de aceitar ou não uma leitura
    suspeita é sempre humana, feita na interface, nunca automática aqui.
    """
    if preco is None:
        return "falha", "preço vazio"
    if faixa_min is not None and preco < faixa_min:
        return "suspeito", f"R${preco:.2f} abaixo da faixa esperada (mín. R${faixa_min:.2f})"
    if faixa_max is not None and preco > faixa_max:
        return "suspeito", f"R${preco:.2f} acima da faixa esperada (máx. R${faixa_max:.2f})"
    return "ok", None
