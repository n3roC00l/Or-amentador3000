"""
Interface de comparação e exportação da cotação de filamentos.

Rodar localmente:
    streamlit run streamlit_app.py

Fonte de verdade é o SQLite (cotacoes.db) — esta tela só lê e formata.
"Exportar para Excel" gera o arquivo no layout do modelo atual sob demanda,
nunca escreve de volta no banco.
"""
import datetime

import pandas as pd
import streamlit as st

from db import conectar, inicializar
from export_excel import gerar as gerar_excel

st.set_page_config(page_title="Cotação de Filamentos", layout="wide")
inicializar()

st.title("Cotação de filamentos")

conn = conectar()
fornecedores = conn.execute("SELECT * FROM fornecedores ORDER BY id").fetchall()
itens = conn.execute("SELECT * FROM itens ORDER BY ordem").fetchall()
cotacoes = {}
for linha in conn.execute("""
    SELECT c.* FROM cotacoes c
    JOIN (
        SELECT item_id, fornecedor_id, MAX(coletado_em) AS ultima
        FROM cotacoes GROUP BY item_id, fornecedor_id
    ) r ON c.item_id = r.item_id AND c.fornecedor_id = r.fornecedor_id
       AND c.coletado_em = r.ultima
"""):
    cotacoes[(linha["item_id"], linha["fornecedor_id"])] = linha
conn.close()

if not fornecedores or not itens:
    st.warning("Banco vazio. Rode `python seed.py` primeiro para popular o catálogo.")
    st.stop()

# --- tabela de comparação -------------------------------------------------
st.subheader("Comparação por item")

linhas_tabela = []
alertas = []
for item in itens:
    linha = {"Item": item["especificacao"], "Qtd": item["quantidade"]}
    precos = {}
    for f in fornecedores:
        cot = cotacoes.get((item["id"], f["id"]))
        if cot and cot["preco_unitario"] is not None and cot["status"] != "falha":
            linha[f["nome"]] = cot["preco_unitario"]
            precos[f["nome"]] = cot["preco_unitario"]
            if cot["status"] == "suspeito":
                alertas.append(f"{f['nome']} / {item['especificacao']}: {cot['mensagem']}")
        else:
            linha[f["nome"]] = None
            motivo = cot["mensagem"] if cot else "sem leitura ainda"
            alertas.append(f"{f['nome']} / {item['especificacao']}: falha — {motivo}")

    if precos:
        mais_barato = min(precos, key=precos.get)
        linha["Mais barato"] = f"{mais_barato} (R${precos[mais_barato]:.2f})"
    else:
        linha["Mais barato"] = "—"
    linhas_tabela.append(linha)

df = pd.DataFrame(linhas_tabela)


def destacar_menor(row):
    precos_row = {f["nome"]: row[f["nome"]] for f in fornecedores if pd.notna(row[f["nome"]])}
    if not precos_row:
        return [""] * len(row)
    menor = min(precos_row.values())
    estilos = []
    for col in row.index:
        if col in precos_row and precos_row[col] == menor:
            estilos.append("background-color: #d4edda")
        else:
            estilos.append("")
    return estilos


st.dataframe(
    df.style.apply(destacar_menor, axis=1).format(
        {f["nome"]: "R${:.2f}" for f in fornecedores}, na_rep="—"
    ),
    use_container_width=True,
)

if alertas:
    with st.expander(f"⚠ {len(alertas)} item(ns) precisam de revisão"):
        for a in alertas:
            st.write("- " + a)

# --- exportação -------------------------------------------------------
st.subheader("Exportar para o financeiro")
objeto = st.text_input("Objeto da cotação", value="Filamentos 3D")

if st.button("Gerar planilha Excel"):
    nome_arquivo = f"mapa_de_cotacao_{datetime.date.today().isoformat()}.xlsx"
    caminho = gerar_excel(objeto, nome_arquivo)
    with open(caminho, "rb") as f:
        st.download_button(
            "Baixar planilha",
            data=f.read(),
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    st.success("Planilha gerada no mesmo layout do modelo atual.")
