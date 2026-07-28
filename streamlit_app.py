"""
Interface de comparação e exportação da cotação de filamentos — Cilla Tech Park.

Rodar localmente:
    streamlit run streamlit_app.py

Fonte de verdade é o SQLite (cotacoes.db). A tela busca cotação nova sozinha
quando os dados têm mais de LIMITE_FRESCOR_MIN, ou por clique em "Atualizar
agora" (ver collector.coletar_tudo). O único campo editável na tela é a
quantidade de cada item — tudo o mais (preços, fornecedor mais barato) é
travado/calculado. Editar quantidade nunca dispara nova coleta, só recalcula
o total a partir do preço já em cache — não bate nas lojas de novo.
"Exportar para Excel" gera o arquivo no layout do modelo atual sob demanda,
nunca escreve de volta no banco.
"""
import datetime

import pandas as pd
import streamlit as st

from collector import coletar_tudo
from db import atualizar_quantidade, conectar, inicializar, ultima_coleta_geral
from export_excel import gerar as gerar_excel

MARCA = "Cilla Tech Park"
COR_MARCA = "#2a78d6"
LIMITE_FRESCOR_MIN = 15

st.set_page_config(page_title="Cotação de Filamentos — Cilla Tech Park", layout="wide", page_icon="🧵")
inicializar()

st.markdown(
    f"""
    <style>
    .ctp-header {{
        display: flex;
        align-items: baseline;
        gap: 0.6rem;
        border-bottom: 3px solid {COR_MARCA};
        padding-bottom: 0.5rem;
        margin-bottom: 0.8rem;
    }}
    .ctp-marca {{
        color: {COR_MARCA};
        font-weight: 700;
        font-size: 1.3rem;
        letter-spacing: 0.01em;
    }}
    .ctp-subtitulo {{
        opacity: 0.7;
        font-size: 1rem;
    }}
    </style>
    <div class="ctp-header">
        <span class="ctp-marca">{MARCA}</span>
        <span class="ctp-subtitulo">Cotação de Filamentos 3D</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def _minutos_desde(iso_str):
    if not iso_str:
        return None
    dt = datetime.datetime.fromisoformat(iso_str)
    return (datetime.datetime.now() - dt).total_seconds() / 60


# --- atualização ao vivo (cache de LIMITE_FRESCOR_MIN + botão manual) -----
col_status, col_botao = st.columns([5, 1])
atualizar_clicado = col_botao.button("🔄 Atualizar agora", use_container_width=True)

conn = conectar()
ultima = ultima_coleta_geral(conn)
conn.close()
idade = _minutos_desde(ultima)
precisa_atualizar = idade is None or idade > LIMITE_FRESCOR_MIN or atualizar_clicado

if precisa_atualizar:
    with st.status("🔵 Buscando cotações nas 3 lojas...", expanded=True) as status:
        barra = st.progress(0.0)

        def _callback(indice, total, texto):
            barra.progress(indice / total)
            status.write(texto)

        resumo = coletar_tudo(progress_callback=_callback)
        status.update(
            label=(f"✅ Cotação atualizada — {resumo['ok']} ok, "
                   f"{resumo['suspeitos']} suspeitos, {resumo['falhas']} falhas"),
            state="complete",
        )
    idade = 0

if idade is None:
    col_status.markdown("🔴 **Sem cotação ainda** — clique em Atualizar agora")
elif idade < 1:
    col_status.markdown("🟢 **Cotação atualizada agora mesmo**")
else:
    col_status.markdown(f"🟢 **Cotação atualizada há {int(idade)} min**")

# --- dados -----------------------------------------------------------------
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

# --- monta a tabela + KPIs ---------------------------------------------
total_mais_barato = 0.0
n_ok = n_suspeito = n_sem_leitura = 0
alertas = []
linhas_tabela = []

for item in itens:
    precos, status_fornecedor = {}, {}
    for f in fornecedores:
        cot = cotacoes.get((item["id"], f["id"]))
        if cot and cot["preco_unitario"] is not None and cot["status"] != "falha":
            precos[f["nome"]] = cot["preco_unitario"]
            status_fornecedor[f["nome"]] = cot["status"]
            if cot["status"] == "suspeito":
                alertas.append(f"{f['nome']} / {item['especificacao']}: {cot['mensagem']}")
        else:
            status_fornecedor[f["nome"]] = "falha"
            motivo = cot["mensagem"] if cot else "sem leitura ainda"
            alertas.append(f"{f['nome']} / {item['especificacao']}: falha — {motivo}")

    linha = {
        "item_id": item["id"],
        "Item": item["especificacao"],
        "Categoria": item["categoria"],
        "Qtd": item["quantidade"],
    }

    if precos:
        mais_barato_nome = min(precos, key=precos.get)
        total_item = precos[mais_barato_nome] * item["quantidade"]
        total_mais_barato += total_item
        linha["Mais barato"] = mais_barato_nome
        linha["Total (mais barato)"] = total_item
    else:
        mais_barato_nome = None
        linha["Mais barato"] = "—"
        linha["Total (mais barato)"] = None

    for f in fornecedores:
        nome = f["nome"]
        st_f = status_fornecedor[nome]
        if st_f == "falha":
            texto = "—"
            n_sem_leitura += 1
        else:
            marcador = "★ " if nome == mais_barato_nome else ""
            sufixo = " ⚠️" if st_f == "suspeito" else ""
            texto = f"{marcador}R$ {precos[nome]:.2f}{sufixo}"
            n_ok += 1 if st_f == "ok" else 0
            n_suspeito += 1 if st_f == "suspeito" else 0
        linha[nome] = texto

    linhas_tabela.append(linha)

df = pd.DataFrame(linhas_tabela)

st.markdown("###")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total (mais econômico)", f"R$ {total_mais_barato:,.2f}")
kpi2.metric("Leituras OK", n_ok)
kpi3.metric("Precisam de revisão", n_suspeito)
kpi4.metric("Sem leitura válida", n_sem_leitura)

# --- tabela editável (só Qtd) --------------------------------------------
st.subheader("Comparação por item")
st.caption("★ = fornecedor mais barato · ⚠️ = leitura precisa de revisão · apenas a coluna **Qtd** é editável")

column_config = {
    "Item": st.column_config.TextColumn(disabled=True),
    "Categoria": st.column_config.TextColumn(disabled=True),
    "Qtd": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.0f"),
    "Mais barato": st.column_config.TextColumn(disabled=True),
    "Total (mais barato)": st.column_config.NumberColumn(disabled=True, format="R$ %.2f"),
}
for f in fornecedores:
    column_config[f["nome"]] = st.column_config.TextColumn(disabled=True)

colunas_visiveis = (
    ["Item", "Categoria", "Qtd"] + [f["nome"] for f in fornecedores] + ["Mais barato", "Total (mais barato)"]
)

editado = st.data_editor(
    df,
    column_config=column_config,
    column_order=colunas_visiveis,
    hide_index=True,
    use_container_width=True,
    key="tabela_itens",
)

mudou = False
conn = conectar()
for _, row in editado.iterrows():
    original = df.loc[df["item_id"] == row["item_id"], "Qtd"].iloc[0]
    if row["Qtd"] != original:
        atualizar_quantidade(conn, int(row["item_id"]), float(row["Qtd"]))
        mudou = True
conn.close()
if mudou:
    st.rerun()

if alertas:
    with st.expander(f"⚠ {len(alertas)} leitura(s) precisam de revisão"):
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
