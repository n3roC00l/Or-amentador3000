-- Schema do sistema de cotação de filamentos
-- SQLite é a fonte de verdade dos dados. O Excel é gerado sob demanda a
-- partir daqui (export_excel.py) — nunca o contrário.

-- Controle de estoque próprio (o que a Cilla Tech Park tem guardado) —
-- fluxo principal a partir de 29/07/2026. `filamentos` é o catálogo de
-- tipos que você decide rastrear (não vem de raspagem de loja nenhuma);
-- `movimentos_estoque` é o histórico de entrada/saída em gramas. O saldo
-- atual NUNCA é uma coluna própria — é sempre a soma do histórico (mesmo
-- princípio de "nunca sobrescreve" já usado em `cotacoes` abaixo), pra dar
-- pra auditar quanto tinha em qualquer data, não só agora.
CREATE TABLE IF NOT EXISTS filamentos (
    id              INTEGER PRIMARY KEY,
    material        TEXT NOT NULL,      -- "PLA", "PETG", "ABS", "TPU"...
    cor             TEXT NOT NULL,
    criado_em       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS movimentos_estoque (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filamento_id    INTEGER NOT NULL REFERENCES filamentos(id),
    tipo            TEXT NOT NULL,      -- 'entrada' | 'saida'
    quantidade_g    REAL NOT NULL,
    motivo          TEXT,
    criado_em       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_movimentos_filamento
    ON movimentos_estoque(filamento_id, criado_em);

-- --- a partir daqui: fluxo antigo de cotação ao vivo (raspagem das 3 lojas
-- e comparação automática de preço). Substituído em 29/07/2026 pelo fluxo
-- de estoque + pedido de cotação manual (ver `estoque.py` e
-- `relatorio_cotacao.py`) — as tabelas ficam dormentes (não removidas: têm
-- histórico real de preço coletado nas 3 lojas, útil como referência) mas
-- nada na interface principal escreve nelas mais. Ainda dá pra rodar
-- `python collector.py` direto por linha de comando se quiser reativar.
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
