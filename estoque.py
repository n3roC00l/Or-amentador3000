"""
Controle de estoque próprio de filamentos — quanto material a Cilla Tech
Park tem guardado, em gramas, por (material, cor).

O saldo nunca é armazenado direto: é sempre a soma de `movimentos_estoque`
(entrada soma, saída subtrai). Isso segue o mesmo princípio já usado em
`cotacoes` — histórico nunca sobrescreve — e permite auditar quanto tinha
guardado em qualquer data, não só agora.
"""
import datetime
import sqlite3

MATERIAIS_COMUNS = ["PLA", "PETG", "ABS", "TPU", "ASA", "HIPS", "Nylon", "PC", "Outro"]


def listar_filamentos(conn: sqlite3.Connection):
    """Cada filamento com seu saldo atual em gramas (0 se nunca teve movimento)."""
    return conn.execute("""
        SELECT f.id, f.material, f.cor, f.criado_em,
               COALESCE(SUM(
                   CASE WHEN m.tipo = 'entrada' THEN m.quantidade_g
                        WHEN m.tipo = 'saida' THEN -m.quantidade_g
                        ELSE 0 END
               ), 0) AS saldo_g
        FROM filamentos f
        LEFT JOIN movimentos_estoque m ON m.filamento_id = f.id
        GROUP BY f.id
        ORDER BY f.material, f.cor
    """).fetchall()


def saldo_de(conn: sqlite3.Connection, filamento_id: int) -> float:
    row = conn.execute("""
        SELECT COALESCE(SUM(
            CASE WHEN tipo = 'entrada' THEN quantidade_g
                 WHEN tipo = 'saida' THEN -quantidade_g
                 ELSE 0 END
        ), 0) AS saldo_g
        FROM movimentos_estoque WHERE filamento_id = ?
    """, (filamento_id,)).fetchone()
    return row["saldo_g"]


def buscar_filamento(conn: sqlite3.Connection, material: str, cor: str):
    """Casamento por material+cor sem diferenciar maiúscula/minúscula nem
    espaço nas pontas — 'PLA'/'pla ' e 'Azul'/'azul' são o mesmo filamento."""
    return conn.execute(
        "SELECT * FROM filamentos WHERE LOWER(TRIM(material)) = LOWER(TRIM(?)) "
        "AND LOWER(TRIM(cor)) = LOWER(TRIM(?))",
        (material, cor),
    ).fetchone()


def adicionar_filamento(
    conn: sqlite3.Connection, material: str, cor: str, quantidade_inicial_g: float = 0.0
) -> tuple[int, bool]:
    """Cadastra um novo tipo de filamento e, se houver quantidade inicial, já
    registra a primeira entrada — sem isso o filamento apareceria com saldo
    0 mesmo já tendo material guardado.

    Se já existir um filamento com o mesmo material+cor, NÃO cria uma linha
    duplicada — mescla registrando a quantidade como entrada no filamento
    existente. Sem essa checagem, cadastrar "PLA Azul" duas vezes fragmentava
    o mesmo estoque em duas linhas (bug real encontrado em revisão).

    Devolve (filamento_id, criado_novo) — `criado_novo` é False quando
    mesclou com um cadastro já existente, pra interface avisar o usuário."""
    existente = buscar_filamento(conn, material, cor)
    if existente:
        filamento_id = existente["id"]
        if quantidade_inicial_g > 0:
            registrar_movimento(
                conn, filamento_id, "entrada", quantidade_inicial_g,
                "estoque adicional (mesclado com cadastro já existente)",
            )
        return filamento_id, False

    agora = datetime.datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO filamentos (material, cor, criado_em) VALUES (?, ?, ?)",
        (material, cor, agora),
    )
    filamento_id = cur.lastrowid
    if quantidade_inicial_g > 0:
        registrar_movimento(conn, filamento_id, "entrada", quantidade_inicial_g, "estoque inicial")
    conn.commit()
    return filamento_id, True


def excluir_filamento(conn: sqlite3.Connection, filamento_id: int):
    """Remove o tipo de filamento e todo o histórico de movimentos dele.
    Ação do usuário explícita (botão "excluir" na interface) — não há
    undo além de recadastrar na mão."""
    conn.execute("DELETE FROM movimentos_estoque WHERE filamento_id = ?", (filamento_id,))
    conn.execute("DELETE FROM filamentos WHERE id = ?", (filamento_id,))
    conn.commit()


def registrar_movimento(
    conn: sqlite3.Connection, filamento_id: int, tipo: str, quantidade_g: float, motivo: str = ""
) -> float:
    """Grava entrada ou saída e devolve o saldo resultante. `tipo` deve ser
    'entrada' ou 'saida'. Saída que deixa o saldo negativo NÃO é bloqueada
    (pode ser gap de lançamento anterior) — só fica visível pra quem olhar
    o saldo, igual o resto do sistema nunca esconde dado suspeito."""
    if tipo not in ("entrada", "saida"):
        raise ValueError(f"tipo de movimento inválido: {tipo!r} (use 'entrada' ou 'saida')")
    if quantidade_g <= 0:
        raise ValueError("quantidade_g deve ser positiva — o sinal vem do campo 'tipo'")

    agora = datetime.datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO movimentos_estoque (filamento_id, tipo, quantidade_g, motivo, criado_em) "
        "VALUES (?, ?, ?, ?, ?)",
        (filamento_id, tipo, quantidade_g, motivo, agora),
    )
    conn.commit()
    return saldo_de(conn, filamento_id)


def historico_de(conn: sqlite3.Connection, filamento_id: int):
    return conn.execute(
        "SELECT * FROM movimentos_estoque WHERE filamento_id = ? ORDER BY criado_em DESC",
        (filamento_id,),
    ).fetchall()


def saldo_por_material(conn: sqlite3.Connection):
    """Saldo agregado por material (soma de todas as cores), maior saldo
    primeiro — alimenta o gráfico de estoque por material da aba Análise."""
    return conn.execute("""
        SELECT f.material,
               COALESCE(SUM(
                   CASE WHEN m.tipo = 'entrada' THEN m.quantidade_g
                        WHEN m.tipo = 'saida' THEN -m.quantidade_g
                        ELSE 0 END
               ), 0) AS saldo_g
        FROM filamentos f
        LEFT JOIN movimentos_estoque m ON m.filamento_id = f.id
        GROUP BY f.material
        ORDER BY saldo_g DESC
    """).fetchall()


def uso_medio_semanal(conn: sqlite3.Connection, min_semanas: float = 1.0) -> dict:
    """Uso médio semanal de cada filamento, calculado sobre TODO o histórico
    de saída: total retirado dividido pelo nº de semanas desde a primeira
    saída registrada até agora ("média de todo o histórico", não média
    móvel — decisão explícita do dono do sistema).

    Um filamento sem nenhuma saída registrada simplesmente não aparece no
    dict devolvido — não existe média pra ele, e isso não é o mesmo que
    "uso zero" (pode só não ter sido consumido ainda, ou o consumo nunca
    foi lançado no sistema). Com menos de `min_semanas` de histórico desde
    a primeira saída, o filamento aparece com `media_semanal_g=None`: dividir
    por uma janela tão curta faz o número disparar (uma única saída de
    ontem "viraria" milhares de gramas/semana extrapolados) — melhor não
    mostrar um número do que mostrar um enganoso.

    Devolve dict: filamento_id -> {"total_saida_g", "semanas_historico",
    "media_semanal_g"}.
    """
    linhas = conn.execute("""
        SELECT filamento_id,
               SUM(quantidade_g) AS total_saida_g,
               MIN(criado_em) AS primeira_saida
        FROM movimentos_estoque
        WHERE tipo = 'saida'
        GROUP BY filamento_id
    """).fetchall()

    agora = datetime.datetime.now()
    resultado = {}
    for linha in linhas:
        primeira = datetime.datetime.fromisoformat(linha["primeira_saida"])
        semanas = (agora - primeira).total_seconds() / (7 * 24 * 3600)
        media = linha["total_saida_g"] / semanas if semanas >= min_semanas else None
        resultado[linha["filamento_id"]] = {
            "total_saida_g": linha["total_saida_g"],
            "semanas_historico": semanas,
            "media_semanal_g": media,
        }
    return resultado
