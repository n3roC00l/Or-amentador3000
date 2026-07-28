"""Conexão e inicialização do banco de cotações."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cotacoes.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar():
    conn = conectar()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()


def cotacoes_mais_recentes(conn: sqlite3.Connection):
    """
    Para cada (item, fornecedor), retorna só a leitura de preço mais
    recente — é o que a interface e a exportação usam. O histórico completo
    continua acessível direto na tabela `cotacoes` para auditoria.
    """
    return conn.execute("""
        SELECT c.*
        FROM cotacoes c
        JOIN (
            SELECT item_id, fornecedor_id, MAX(coletado_em) AS ultima
            FROM cotacoes
            GROUP BY item_id, fornecedor_id
        ) mais_recente
        ON c.item_id = mais_recente.item_id
        AND c.fornecedor_id = mais_recente.fornecedor_id
        AND c.coletado_em = mais_recente.ultima
    """).fetchall()


if __name__ == "__main__":
    inicializar()
    print(f"Banco inicializado em {DB_PATH}")
