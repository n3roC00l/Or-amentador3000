"""
Interface Cilla Tech Park — controle de estoque de filamentos + pedido de
cotação para fornecedores.

Rodar localmente:
    streamlit run streamlit_app.py

Tema visual (paleta, tipografia, tokens de tabela) fica em
`.streamlit/config.toml`. O CSS neste arquivo cobre só o que o tema do
Streamlit não alcança: anatomia de card, ícones (Material Symbols Rounded,
zero emoji) e o botão "Excluir" como ação destrutiva. Guia completo de
design (paleta/tipografia/ícones) em `DESIGN.md` — qualquer ajuste visual
aqui deveria primeiro atualizar aquele arquivo.

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
COR_BORDA = "#e2e6ee"
COR_ERRO_TEXTO = "#b3261e"
COR_ERRO_FUNDO = "#fdecea"

# só os ícones realmente usados na tela — mantém o download da fonte pequeno
# em vez de puxar o conjunto inteiro do Material Symbols.
_ICONES_USADOS = "inventory_2,description,add,swap_horiz,delete,history,request_quote,download,search"
_FONTE_ICONES = (
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:"
    f"opsz,wght,FILL,GRAD@20,400,0,0&icon_names={_ICONES_USADOS}"
)

st.set_page_config(page_title="Filamentos — Cilla Tech Park", layout="wide", page_icon="🧵")
inicializar()

st.markdown(
    f"""
    <style>
    @import url('{_FONTE_ICONES}');

    .md-icon {{
        font-family: 'Material Symbols Rounded';
        font-weight: normal;
        font-style: normal;
        font-size: 20px;
        line-height: 1;
        vertical-align: -4px;
        display: inline-block;
    }}

    .ctp-header {{
        display: flex;
        align-items: baseline;
        gap: 0.7rem;
        border-bottom: 2px solid {COR_MARCA};
        padding-bottom: 0.7rem;
        margin-bottom: 1.4rem;
    }}
    .ctp-marca {{
        color: {COR_MARCA};
        font-weight: 700;
        font-size: 1.375rem;
        letter-spacing: 0.01em;
    }}
    .ctp-subtitulo {{
        color: #5b6472;
        font-size: 0.9375rem;
    }}

    .ctp-secao {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.0625rem;
        font-weight: 600;
        color: #1a1f2b;
        margin: 0 0 0.7rem 0;
    }}
    .ctp-secao .md-icon {{
        color: {COR_MARCA};
    }}

    /* cards: formulários e o container da coluna Excluir recebem a mesma
       superfície branca elevada sobre o fundo cinza da página — sem isso
       cada seção era só uma caixa com borda fina genérica do Streamlit. */
    div[data-testid="stForm"], [class*="st-key-card_"] {{
        background: #ffffff;
        border: 1px solid {COR_BORDA};
        border-radius: 0.6rem;
        padding: 1.25rem 1.25rem 1rem 1.25rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}

    /* botão Excluir tratado como ação destrutiva (contorno/texto na cor de
       erro), não mais um botão azul de marca igual aos de ação principal —
       evita que pareça "só mais um botão" e reduz risco de clique
       acidental. */
    .st-key-card_excluir div[data-testid="stButton"] button {{
        border-color: {COR_ERRO_TEXTO} !important;
        color: {COR_ERRO_TEXTO} !important;
        background: #ffffff !important;
    }}
    .st-key-card_excluir div[data-testid="stButton"] button:hover:not(:disabled) {{
        background: {COR_ERRO_FUNDO} !important;
    }}
    .st-key-card_excluir div[data-testid="stButton"] button:disabled {{
        border-color: {COR_BORDA} !important;
        color: #98a1b0 !important;
        background: #ffffff !important;
    }}
    </style>
    <div class="ctp-header">
        <span class="ctp-marca">{MARCA}</span>
        <span class="ctp-subtitulo">Estoque e Cotação de Filamentos 3D</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def _titulo_secao(icone: str, texto: str):
    """Título de seção/card padronizado: ícone Material Symbols + texto,
    mesmo papel tipográfico em toda a tela (ver DESIGN.md)."""
    st.markdown(
        f'<div class="ctp-secao"><span class="md-icon">{icone}</span>{texto}</div>',
        unsafe_allow_html=True,
    )


aba_estoque, aba_cotacao = st.tabs(["Estoque", "Cotação"])


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
    # dict, não sqlite3.Row: os selectbox abaixo usam a própria linha do
    # filamento como opção (não uma string derivada como chave de dict — ver
    # comentário no form de movimento), e o Streamlit precisa conseguir
    # fazer deepcopy do valor do widget pra guardar em session_state.
    # sqlite3.Row não suporta isso (TypeError: cannot pickle 'sqlite3.Row'
    # object — encontrado rodando a suíte de regressão, não só em teoria).
    filamentos = [dict(f) for f in estoque.listar_filamentos(conn)]
    conn.close()

    # separador de milhar em vírgula por padrão, igual às colunas das tabelas
    # abaixo (column_config usa "%,.0f") — mesmo formato em toda a tela, sem
    # misturar convenção BR (ponto) com a das tabelas (vírgula).
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Tipos de filamento cadastrados", f"{len(filamentos):,}")
    kpi2.metric("Total em estoque", f"{sum(f['saldo_g'] for f in filamentos):,.0f} g")

    _titulo_secao("inventory_2", "Filamentos em estoque")
    if filamentos:
        busca = st.text_input(
            "Buscar", placeholder="Filtrar por material ou cor…",
            label_visibility="collapsed", icon=":material/search:",
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
        st.info("Nenhum filamento cadastrado ainda — adicione um abaixo.", icon=":material/inventory_2:")

    st.markdown("###")
    col_add, col_mov, col_del = st.columns(3)

    with col_add:
        with st.form("form_add_filamento", clear_on_submit=True):
            _titulo_secao("add", "Adicionar filamento")
            material = st.selectbox("Material", estoque.MATERIAIS_COMUNS)
            material_livre = st.text_input("Material (se escolheu \"Outro\")", disabled=material != "Outro")
            cor = st.text_input("Cor")
            qtd_inicial = st.number_input("Quantidade inicial (g)", min_value=0.0, step=100.0)
            if st.form_submit_button("Adicionar", width="stretch", icon=":material/add:"):
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
        if filamentos:
            with st.form("form_movimento"):
                _titulo_secao("swap_horiz", "Registrar entrada/saída")
                # a opção do selectbox é a própria linha do filamento (não uma
                # string "Material Cor (saldo X g)" usada como chave de dict) —
                # essa string embutia o saldo, que muda toda hora; se o saldo
                # mudasse entre o filamento aparecer na tela e o form ser
                # enviado (ex.: outra aba/pessoa mexendo no mesmo estoque), a
                # string selecionada deixava de bater com qualquer opção nova
                # e o Streamlit reseta a seleção pro primeiro item da lista
                # silenciosamente — risco de registrar o movimento no
                # filamento errado sem aviso nenhum.
                escolha = st.selectbox(
                    "Filamento", filamentos, key="select_movimento",
                    format_func=lambda f: f"{f['material']} {f['cor']} (saldo {f['saldo_g']:.0f} g)",
                )
                tipo = st.radio("Tipo", ["entrada", "saida"], horizontal=True, format_func=lambda t: "Entrada" if t == "entrada" else "Saída")
                quantidade = st.number_input("Quantidade (g)", min_value=0.0, step=50.0)
                motivo = st.text_input("Motivo", placeholder="ex.: compra 3DFILA NF 1234, consumo peça X")
                if st.form_submit_button("Registrar", width="stretch", icon=":material/swap_horiz:"):
                    if quantidade <= 0:
                        st.error("Quantidade precisa ser maior que zero.")
                    else:
                        conn = conectar()
                        novo_saldo = estoque.registrar_movimento(conn, escolha["id"], tipo, quantidade, motivo)
                        conn.close()
                        st.success(f"Registrado. Novo saldo: {novo_saldo:,.0f} g")
                        st.rerun()
        else:
            with st.container(key="card_registrar_vazio"):
                _titulo_secao("swap_horiz", "Registrar entrada/saída")
                st.caption("Cadastre um filamento primeiro.")

    with col_del:
        with st.container(key="card_excluir"):
            _titulo_secao("delete", "Excluir filamento")
            if filamentos:
                escolha_del = st.selectbox(
                    "Filamento", filamentos, key="select_excluir",
                    format_func=lambda f: f"{f['material']} {f['cor']}",
                )
                confirmar = st.checkbox("Confirmo a exclusão (apaga o histórico desse filamento)")
                # a checagem de `confirmar` aqui dentro é proposital, não redundante com
                # `disabled=not confirmar` acima: `disabled` só impede o clique na
                # interface real (JS do navegador); sem essa segunda checagem, uma
                # chamada direta ao callback do botão apagaria o filamento mesmo sem
                # confirmação.
                if st.button(
                    "Excluir", disabled=not confirmar, width="stretch", icon=":material/delete:"
                ) and confirmar:
                    conn = conectar()
                    estoque.excluir_filamento(conn, escolha_del["id"])
                    conn.close()
                    st.success(f"{escolha_del['material']} {escolha_del['cor']} excluído.")
                    st.rerun()
            else:
                st.caption("Nada para excluir.")

    if filamentos:
        with st.expander("Histórico de movimentações", icon=":material/history:"):
            escolha_hist = st.selectbox(
                "Filamento", filamentos, key="select_historico",
                format_func=lambda f: f"{f['material']} {f['cor']}",
            )
            conn = conectar()
            historico = estoque.historico_de(conn, escolha_hist["id"])
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
    _titulo_secao("description", "Selecionar filamentos para cotação")
    st.caption(
        "Escolha quais filamentos você precisa comprar e quanto — a tela gera "
        "uma planilha simples (material, cor, quantidade) pra mandar pras "
        "empresas cotarem. Sem coluna de preço: isso é a empresa quem preenche."
    )

    conn = conectar()
    filamentos_cot = estoque.listar_filamentos(conn)
    conn.close()

    if not filamentos_cot:
        st.warning("Cadastre filamentos na aba Estoque primeiro.", icon=":material/inventory_2:")
        st.stop()

    # Estado de seleção guardado por filamento_id em session_state — NUNCA
    # confiar só no que st.data_editor devolve posicionalmente. Bug real:
    # o data_editor rastreia edições como "posição da linha -> coluna ->
    # valor" (streamlit/elements/widgets/data_editor.py, docstring de
    # `edited_rows`), não por identidade da linha. Como a tabela abaixo é
    # reconstruída a cada rerun a partir da lista FILTRADA pela busca, o
    # número/ordem das linhas muda conforme o texto digitado — e o
    # Streamlit reaplicava a edição salva na "posição 2", por exemplo, em
    # cima de qualquer filamento que passasse a ocupar a posição 2 depois
    # do filtro mudar. Resultado: marcar/preencher quantidade de um
    # filamento, mexer na busca, e a seleção "pulava" pra outro filamento
    # sem aviso — o bug relatado. Guardando por id e sempre reconstruindo a
    # tabela a partir desse estado (não de zeros), a exibição fica correta
    # não importa o que o filtro mostrar a cada rerun, e selecionar itens
    # em buscas diferentes soma no mesmo pedido em vez de se perder.
    if "cotacao_selecao" not in st.session_state:
        st.session_state.cotacao_selecao = {}  # filamento_id -> quantidade_g

    busca_cot = st.text_input(
        "Buscar", placeholder="Filtrar por material ou cor…", label_visibility="collapsed",
        key="busca_cotacao", icon=":material/search:",
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
            "id": f["id"],
            "Selecionar": f["id"] in st.session_state.cotacao_selecao,
            "Material": f["material"],
            "Cor": f["cor"],
            "Saldo atual (g)": f["saldo_g"],
            "Quantidade necessária (g)": st.session_state.cotacao_selecao.get(f["id"], 0.0),
        }
        for f in filamentos_filtrados_cot
    ])

    # a `key` do editor muda junto com o CONJUNTO de ids visíveis (não só
    # com o texto da busca — adicionar/excluir filamento noutra aba também
    # muda o conjunto). Isso é a segunda metade da correção do bug acima:
    # sem isso, o Streamlit reaproveita o estado interno do editor antigo
    # (guardado por posição) e reaplica a edição da "posição 2" em cima do
    # que quer que esteja na posição 2 da tabela NOVA — reconstruir
    # `df_sel` a partir do session_state (acima) não adianta se o próprio
    # data_editor reintroduz a mesma corrupção por baixo. Com a chave
    # trocando, cada conjunto de linhas diferente é um widget novo, sem
    # edição antiga nenhuma pra reaplicar errado — e como `df_sel` já vem
    # montada a partir do session_state, nada se perde visualmente.
    chave_editor = "tabela_cotacao_" + str(hash(tuple(f["id"] for f in filamentos_filtrados_cot)))
    editado = st.data_editor(
        df_sel,
        column_order=["Selecionar", "Material", "Cor", "Saldo atual (g)", "Quantidade necessária (g)"],
        column_config={
            "Selecionar": st.column_config.CheckboxColumn(),
            "Material": st.column_config.TextColumn(disabled=True),
            "Cor": st.column_config.TextColumn(disabled=True),
            "Saldo atual (g)": st.column_config.NumberColumn(disabled=True, format="%,.0f"),
            "Quantidade necessária (g)": st.column_config.NumberColumn(min_value=0.0, step=100.0, format="%,.0f"),
        },
        hide_index=True,
        width="stretch",
        key=chave_editor,
    )

    # persiste de volta por id imediatamente — é o passo que fecha o bug:
    # cada rerun consome o que está visível AGORA (correto nesta mesma
    # passada) e grava por id, então uma busca diferente no próximo rerun
    # não reaplica a edição na posição errada.
    for _, row in editado.iterrows():
        fid = row["id"]
        if row["Selecionar"] and row["Quantidade necessária (g)"] > 0:
            st.session_state.cotacao_selecao[fid] = row["Quantidade necessária (g)"]
        else:
            st.session_state.cotacao_selecao.pop(fid, None)

    objeto = st.text_input("Objeto do pedido", value="Reposição de estoque")

    # fonte da verdade é o session_state (cobre seleções feitas em qualquer
    # busca, não só o que está visível agora) — `por_id.get` ignora
    # silenciosamente um id que tenha sido excluído do estoque nesse meio
    # tempo, em vez de quebrar a geração do relatório.
    por_id = {f["id"]: f for f in filamentos_cot}
    itens_pedido = [
        {"material": por_id[fid]["material"], "cor": por_id[fid]["cor"], "quantidade_g": qtd}
        for fid, qtd in st.session_state.cotacao_selecao.items()
        if fid in por_id
    ]

    if st.button("Gerar pedido de cotação (Excel)", type="primary", icon=":material/request_quote:"):
        if not itens_pedido:
            st.error("Selecione ao menos um filamento com quantidade maior que zero.")
        else:
            nome_arquivo = f"pedido_de_cotacao_{datetime.date.today().isoformat()}.xlsx"
            caminho = gerar_relatorio(itens_pedido, objeto=objeto, caminho_saida=nome_arquivo)
            with open(caminho, "rb") as f:
                st.download_button(
                    "Baixar pedido de cotação",
                    data=f.read(),
                    file_name=nome_arquivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    icon=":material/download:",
                )
            st.success(f"Pedido gerado com {len(itens_pedido)} item(ns).")
