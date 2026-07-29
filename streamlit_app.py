"""
Interface Cilla Tech Park — controle de estoque de filamentos + pedido de
cotação para fornecedores.

Rodar localmente:
    streamlit run streamlit_app.py

Tema visual e chrome de UI (cor da marca, ocultar toolbar de dev) ficam em
`.streamlit/config.toml` — não aqui, é onde o Streamlit espera.

Fonte de verdade é o SQLite (cotacoes.db). Duas abas:

- **Estoque**: cadastro dos tipos de filamento (material + cor) que você
  guarda, com saldo em gramas calculado a partir do histórico de
  movimentações (nunca uma coluna solta que alguém sobrescreve por engano —
  ver `estoque.py`). Dá pra adicionar filamento novo, registrar
  entrada/saída e excluir um tipo (com confirmação, porque isso apaga o
  histórico dele). Adicionar um material+cor que já existe MESCLA com o
  cadastro existente em vez de duplicar linha (bug real corrigido em
  29/07/2026 — ver docstring de `estoque.adicionar_filamento`).
- **Cotação**: você escolhe quais filamentos precisa comprar e quanto, e a
  tela gera uma planilha simples (material/cor/quantidade) pra mandar pras
  empresas cotarem — sem coluna de preço, porque isso é a empresa quem
  preenche na resposta. Não faz mais raspagem automática das lojas (esse
  fluxo antigo continua existindo em `collector.py`, mas dormente — rode
  por linha de comando se quiser reativar).
"""
import datetime

import pandas as pd
import streamlit as st

import estoque
from db import conectar, inicializar
from relatorio_cotacao import gerar as gerar_relatorio

MARCA = "Cilla Tech Park"
COR_MARCA = "#2a78d6"

st.set_page_config(page_title="Filamentos — Cilla Tech Park", layout="wide", page_icon="🧵")
inicializar()

st.markdown(
    f"""
    <style>
    .ctp-header {{
        display: flex;
        align-items: baseline;
        gap: 0.7rem;
        border-bottom: 3px solid {COR_MARCA};
        padding-bottom: 0.7rem;
        margin-bottom: 1.4rem;
    }}
    .ctp-marca {{
        color: {COR_MARCA};
        font-weight: 700;
        font-size: 1.5rem;
        letter-spacing: 0.01em;
    }}
    .ctp-subtitulo {{
        opacity: 0.65;
        font-size: 1rem;
    }}
    /* aproxima o rótulo dos widgets do controle, títulos de seção com peso
       maior — reduz o aspecto "formulário cru" padrão do Streamlit */
    div[data-testid="stForm"] {{
        border: 1px solid rgba(49, 51, 63, 0.15);
        border-radius: 0.6rem;
        padding: 1.2rem 1.2rem 0.6rem 1.2rem;
    }}
    </style>
    <div class="ctp-header">
        <span class="ctp-marca">{MARCA}</span>
        <span class="ctp-subtitulo">Estoque e Cotação de Filamentos 3D</span>
    </div>
    """,
    unsafe_allow_html=True,
)

aba_estoque, aba_cotacao = st.tabs(["📦 Estoque", "📋 Cotação"])


def _tabela_filamentos(lista, incluir_kg=True):
    """DataFrame com o mesmo formato usado nas duas abas — datas e números
    formatados de forma consistente (mesmo separador de milhar dos KPIs,
    em vez de número cru)."""
    linhas = []
    for f in lista:
        linha = {
            "Material": f["material"],
            "Cor": f["cor"],
            "Saldo (g)": f["saldo_g"],
        }
        if incluir_kg:
            linha["Saldo (kg)"] = round(f["saldo_g"] / 1000, 3)
        linha["Cadastrado em"] = pd.to_datetime(f["criado_em"])
        linhas.append(linha)
    return pd.DataFrame(linhas)


# ============================================================ ESTOQUE ====
with aba_estoque:
    conn = conectar()
    filamentos = estoque.listar_filamentos(conn)
    conn.close()

    # separador de milhar em vírgula por padrão, igual às colunas das tabelas
    # abaixo (column_config usa "%,.0f") — mesmo formato em toda a tela, sem
    # misturar convenção BR (ponto) com a das tabelas (vírgula).
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Tipos de filamento cadastrados", f"{len(filamentos):,}")
    kpi2.metric("Total em estoque", f"{sum(f['saldo_g'] for f in filamentos):,.0f} g")

    st.subheader("Filamentos em estoque")
    if filamentos:
        busca = st.text_input(
            "Buscar", placeholder="Filtrar por material ou cor…", label_visibility="collapsed"
        )
        filtrados = filamentos
        if busca.strip():
            alvo = busca.strip().lower()
            filtrados = [
                f for f in filamentos
                if alvo in f["material"].lower() or alvo in f["cor"].lower()
            ]

        if filtrados:
            df_estoque = _tabela_filamentos(filtrados)
            st.dataframe(
                df_estoque,
                hide_index=True,
                width="stretch",
                column_config={
                    "Saldo (g)": st.column_config.NumberColumn(format="%,.0f"),
                    "Saldo (kg)": st.column_config.NumberColumn(format="%,.2f"),
                    "Cadastrado em": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                },
            )
        else:
            st.caption(f"Nenhum filamento bate com \"{busca}\".")
    else:
        st.info("Nenhum filamento cadastrado ainda — adicione um abaixo.")

    st.markdown("###")
    col_add, col_mov, col_del = st.columns(3)

    with col_add:
        st.markdown("**➕ Adicionar filamento**")
        with st.form("form_add_filamento", clear_on_submit=True):
            material = st.selectbox("Material", estoque.MATERIAIS_COMUNS)
            material_livre = st.text_input("Material (se escolheu \"Outro\")", disabled=material != "Outro")
            cor = st.text_input("Cor")
            qtd_inicial = st.number_input("Quantidade inicial (g)", min_value=0.0, step=100.0)
            if st.form_submit_button("Adicionar", width="stretch"):
                material_final = material_livre.strip() if material == "Outro" else material
                if not material_final or not cor.strip():
                    st.error("Preencha material e cor.")
                else:
                    conn = conectar()
                    _, criado_novo = estoque.adicionar_filamento(conn, material_final, cor.strip(), qtd_inicial)
                    conn.close()
                    if criado_novo:
                        st.success(f"{material_final} {cor.strip()} adicionado.")
                    else:
                        st.success(
                            f"{material_final} {cor.strip()} já existia — "
                            f"mesclado (quantidade somada ao estoque existente)."
                        )
                    st.rerun()

    with col_mov:
        st.markdown("**🔁 Registrar entrada/saída**")
        if filamentos:
            with st.form("form_movimento"):
                opcoes = {f"{f['material']} {f['cor']} (saldo {f['saldo_g']:.0f} g)": f["id"] for f in filamentos}
                escolha = st.selectbox("Filamento", list(opcoes.keys()))
                tipo = st.radio("Tipo", ["entrada", "saida"], horizontal=True, format_func=lambda t: "Entrada" if t == "entrada" else "Saída")
                quantidade = st.number_input("Quantidade (g)", min_value=0.0, step=50.0)
                motivo = st.text_input("Motivo", placeholder="ex.: compra 3DFILA NF 1234, consumo peça X")
                if st.form_submit_button("Registrar", width="stretch"):
                    if quantidade <= 0:
                        st.error("Quantidade precisa ser maior que zero.")
                    else:
                        conn = conectar()
                        novo_saldo = estoque.registrar_movimento(conn, opcoes[escolha], tipo, quantidade, motivo)
                        conn.close()
                        st.success(f"Registrado. Novo saldo: {novo_saldo:,.0f} g")
                        st.rerun()
        else:
            st.caption("Cadastre um filamento primeiro.")

    with col_del:
        st.markdown("**🗑️ Excluir filamento**")
        if filamentos:
            with st.container(border=True):
                opcoes_del = {f"{f['material']} {f['cor']}": f["id"] for f in filamentos}
                escolha_del = st.selectbox("Filamento", list(opcoes_del.keys()), key="select_excluir")
                confirmar = st.checkbox("Confirmo a exclusão (apaga o histórico desse filamento)")
                # a checagem de `confirmar` aqui dentro é proposital, não redundante com
                # `disabled=not confirmar` acima: `disabled` só impede o clique na
                # interface real (JS do navegador); sem essa segunda checagem, uma
                # chamada direta ao callback do botão apagaria o filamento mesmo sem
                # confirmação.
                if st.button("Excluir", type="primary", disabled=not confirmar, width="stretch") and confirmar:
                    conn = conectar()
                    estoque.excluir_filamento(conn, opcoes_del[escolha_del])
                    conn.close()
                    st.success(f"{escolha_del} excluído.")
                    st.rerun()
        else:
            st.caption("Nada para excluir.")

    if filamentos:
        with st.expander("🕘 Histórico de movimentações"):
            opcoes_hist = {f"{f['material']} {f['cor']}": f["id"] for f in filamentos}
            escolha_hist = st.selectbox("Filamento", list(opcoes_hist.keys()), key="select_historico")
            conn = conectar()
            historico = estoque.historico_de(conn, opcoes_hist[escolha_hist])
            conn.close()
            if historico:
                df_hist = pd.DataFrame([
                    {
                        "Data": pd.to_datetime(h["criado_em"]),
                        "Tipo": "Entrada" if h["tipo"] == "entrada" else "Saída",
                        "Quantidade (g)": h["quantidade_g"],
                        "Motivo": h["motivo"],
                    }
                    for h in historico
                ])
                st.dataframe(
                    df_hist,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Data": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                        "Quantidade (g)": st.column_config.NumberColumn(format="%,.0f"),
                    },
                )
            else:
                st.caption("Sem movimentações ainda.")

# ============================================================ COTAÇÃO ====
with aba_cotacao:
    st.caption(
        "Escolha quais filamentos você precisa comprar e quanto — a tela gera "
        "uma planilha simples (material, cor, quantidade) pra mandar pras "
        "empresas cotarem. Sem coluna de preço: isso é a empresa quem preenche."
    )

    conn = conectar()
    filamentos_cot = estoque.listar_filamentos(conn)
    conn.close()

    if not filamentos_cot:
        st.warning("Cadastre filamentos na aba Estoque primeiro.")
        st.stop()

    busca_cot = st.text_input(
        "Buscar", placeholder="Filtrar por material ou cor…", label_visibility="collapsed", key="busca_cotacao"
    )
    filamentos_filtrados_cot = filamentos_cot
    if busca_cot.strip():
        alvo = busca_cot.strip().lower()
        filamentos_filtrados_cot = [
            f for f in filamentos_cot
            if alvo in f["material"].lower() or alvo in f["cor"].lower()
        ]

    df_sel = pd.DataFrame([
        {
            "Selecionar": False,
            "Material": f["material"],
            "Cor": f["cor"],
            "Saldo atual (g)": f["saldo_g"],
            "Quantidade necessária (g)": 0.0,
        }
        for f in filamentos_filtrados_cot
    ])

    editado = st.data_editor(
        df_sel,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn(),
            "Material": st.column_config.TextColumn(disabled=True),
            "Cor": st.column_config.TextColumn(disabled=True),
            "Saldo atual (g)": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
            "Quantidade necessária (g)": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%,.0f"),
        },
        hide_index=True,
        width="stretch",
        key="tabela_cotacao",
    )

    objeto = st.text_input("Objeto do pedido", value="Reposição de estoque")

    selecionados = editado[(editado["Selecionar"]) & (editado["Quantidade necessária (g)"] > 0)]

    if st.button("📤 Gerar pedido de cotação (Excel)", type="primary"):
        if selecionados.empty:
            st.error("Selecione ao menos um filamento com quantidade maior que zero.")
        else:
            itens_pedido = [
                {
                    "material": row["Material"],
                    "cor": row["Cor"],
                    "quantidade_g": row["Quantidade necessária (g)"],
                }
                for _, row in selecionados.iterrows()
            ]
            nome_arquivo = f"pedido_de_cotacao_{datetime.date.today().isoformat()}.xlsx"
            caminho = gerar_relatorio(itens_pedido, objeto=objeto, caminho_saida=nome_arquivo)
            with open(caminho, "rb") as f:
                st.download_button(
                    "⬇️ Baixar pedido de cotação",
                    data=f.read(),
                    file_name=nome_arquivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            st.success(f"Pedido gerado com {len(itens_pedido)} item(ns).")
