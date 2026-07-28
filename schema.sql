-- Schema do sistema de cotação de filamentos
-- SQLite é a fonte de verdade dos dados. O Excel é gerado sob demanda a
-- partir daqui (export_excel.py) — nunca o contrário.

CREATE TABLE IF NOT EXISTS fornecedores (
    id                  INTEGER PRIMARY KEY,
    nome                TEXT NOT NULL UNIQUE,      -- "3DFILA", "3DLAB", "F3D"
    site                TEXT,
    condicao_pagamento  TEXT,                      -- ex.: "à vista"
    prazo_entrega       TEXT,                       -- ex.: "15 dias"
    frete               REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS itens (
    id              INTEGER PRIMARY KEY,
    ordem           INTEGER,
    especificacao   TEXT NOT NULL,      -- "PLA Amarelo"
    quantidade      REAL NOT NULL,
    unidade         TEXT DEFAULT 'UN',
    categoria       TEXT,               -- "PLA", "PETG", "ABS" — usada na validação de faixa
    faixa_min       REAL,               -- preço unitário plausível mínimo p/ essa categoria
    faixa_max       REAL                -- preço unitário plausível máximo p/ essa categoria
);

-- URL do produto específico em cada fornecedor. Só existe linha aqui quando
-- a URL já é conhecida — é o que separa "revisitar preço" de "descobrir produto".
CREATE TABLE IF NOT EXISTS urls_produto (
    item_id         INTEGER NOT NULL REFERENCES itens(id),
    fornecedor_id   INTEGER NOT NULL REFERENCES fornecedores(id),
    url             TEXT NOT NULL,
    PRIMARY KEY (item_id, fornecedor_id)
);

-- Histórico de leituras de preço. NUNCA sobrescreve — cada coleta gera uma
-- nova linha, então dá pra auditar preço ao longo do tempo e nunca se perde
-- o "método usado" (parser vs IA) nem o motivo de uma leitura suspeita/falha.
CREATE TABLE IF NOT EXISTS cotacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         INTEGER NOT NULL REFERENCES itens(id),
    fornecedor_id   INTEGER NOT NULL REFERENCES fornecedores(id),
    preco_unitario  REAL,               -- NULL quando status = 'falha'
    metodo          TEXT NOT NULL,      -- 'parser' | 'ia' | 'manual'
    status          TEXT NOT NULL,      -- 'ok' | 'suspeito' | 'falha'
    mensagem        TEXT,
    coletado_em     TEXT NOT NULL       -- timestamp ISO 8601
);

CREATE INDEX IF NOT EXISTS idx_cotacoes_item_fornecedor
    ON cotacoes(item_id, fornecedor_id, coletado_em);
