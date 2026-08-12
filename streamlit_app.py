"""
Interface Cilla Tech Park — controle de estoque de filamentos + pedido de
cotação para fornecedores.

Rodar localmente:
    streamlit run streamlit_app.py

Tema visual (paleta, tipografia, tokens de tabela) fica em
`.streamlit/config.toml`, que define claro E escuro (`[theme.light]`/
`[theme.dark]`) — o usuário troca no menu nativo "☰" → Settings → Theme. O
CSS neste arquivo cobre só o que o tema nativo não alcança (cabeçalho, card,
ícones, botão "Excluir" como ação destrutiva) e por isso lê `st.context.
theme.type` pra saber qual paleta usar nesses elementos customizados — sem
isso o cabeçalho/cards ficariam presos no claro mesmo com o resto da tela em
modo escuro. Guia completo de design (paleta/tipografia/ícones) em
`DESIGN.md` — qualquer ajuste visual aqui deveria primeiro atualizar aquele
arquivo.

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
import base64
import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import estoque
from db import conectar, inicializar
from relatorio_cotacao import gerar as gerar_relatorio

MARCA = "Cilla Tech Park"
_LOGO_PATH = Path(__file__).parent / "logo.jpg"

st.set_page_config(page_title="Filamentos — Cilla Tech Park", layout="wide", page_icon="🧵")
inicializar()

# Tema ativo (claro/escuro), escolhido pelo usuário no menu nativo do
# Streamlit ("☰" → Settings → Theme — ver .streamlit/config.toml). Lido aqui
# porque o CSS customizado deste arquivo (cabeçalho, cards, ícones) não é
# alcançado pelo tema nativo, que só cobre os próprios widgets do Streamlit
# (botão, campo, tabela); sem reler o tema aqui esses elementos ficariam
# presos no claro mesmo com o resto da tela em modo escuro.
# `st.context.theme.type` pode vir incorreto por 1 run logo após o usuário
# trocar de tema (limitação documentada do Streamlit, não bug nosso) — sem
# consequência séria aqui, corrige sozinho no run seguinte.
_ESCURO = (st.context.theme.type or "light") == "dark"

# paleta alinhada ao Espaço Maker CTP (espa-o-maker.vercel.app) — ver
# DESIGN.md. Par claro/escuro: os valores claros são os originais (usados
# desde 29/07/2026); os escuros foram conferidos com o validador de
# contraste da skill de dataviz contra o fundo `#0a1628` antes de entrar
# aqui (todos ≥ 4.5:1 — ver .streamlit/config.toml pro detalhe por cor).
if _ESCURO:
    COR_MARCA = "#3987e5"
    COR_SUPERFICIE = "#13233a"
    COR_BORDA = "#24354c"
    COR_TEXTO = "#f2f5f9"
    COR_TEXTO_SECUNDARIO = "#b8c4d4"
    COR_TEXTO_MUTED = "#5b7590"
    COR_ERRO_TEXTO = "#ff8a8a"
    COR_ERRO_FUNDO = "#3a1518"
    COR_ATENCAO_TEXTO = "#ffb84d"
    COR_ATENCAO_FUNDO = "#3a2a10"
    COR_SUCESSO_TEXTO = "#a1f01f"
    COR_SUCESSO_FUNDO = "#1f2e0a"
else:
    COR_MARCA = "#063a70"
    COR_SUPERFICIE = "#ffffff"
    COR_BORDA = "#e2e8f0"
    COR_TEXTO = "#0a1628"
    COR_TEXTO_SECUNDARIO = "#4b5769"
    COR_TEXTO_MUTED = "#8898aa"
    COR_ERRO_TEXTO = "#b3261e"
    COR_ERRO_FUNDO = "#fdecea"
    COR_ATENCAO_TEXTO = "#a15c00"
    COR_ATENCAO_FUNDO = "#fdf3e3"
    COR_SUCESSO_TEXTO = "#3f6212"
    COR_SUCESSO_FUNDO = "#d4f89e"

# faixas de alerta de saldo baixo na tabela de estoque (pedido explícito do
# dono do sistema) — reusa as mesmas cores semânticas de erro/atenção/
# sucesso já usadas em st.error/warning/success no resto do app, em vez de
# introduzir uma paleta nova só pra isso.
LIMITE_CRITICO_KG = 1.0
LIMITE_ATENCAO_KG = 3.0

# painel "centro de controle" da aba Análise — fica escuro sempre, mesmo
# com o resto do app no tema claro (não usa `_ESCURO`: é uma escolha visual
# fixa pra aquele painel, independente do tema escolhido pelo usuário no
# menu nativo). Fundo e "marca escura" são os tons documentados em
# DESIGN.md (`#021e3a`), até então "uso futuro". O azul-glow das barras é
# um degrau mais claro da MESMA família de
# marca (não o lime): lime é reservado a indicador de status/sucesso em
# todo o resto do sistema — usá-lo pra codificar quantidade nas barras
# quebraria essa convenção e faria a barra mais alta parecer um alerta de
# "sucesso" em vez de só "maior valor". Contraste de todas as cores abaixo
# contra o fundo escuro conferido com o validador da skill de dataviz antes
# de usar (branco 16.8:1, glow 4.6:1, texto secundário 9.5:1, lime 12:1).
COR_ESCURO_FUNDO = "#021e3a"
COR_ESCURO_GLOW = "#3987e5"
COR_ESCURO_TEXTO_SECUNDARIO = "#b8c4d4"
COR_STATUS_AO_VIVO = "#a1f01f"

# aba Análise: intervalo de auto-atualização do gráfico/tabela via
# st.fragment(run_every=...) — ver seção ANÁLISE mais abaixo.
INTERVALO_ATUALIZACAO_S = 15

# só os ícones realmente usados na tela — mantém o download da fonte pequeno
# em vez de puxar o conjunto inteiro do Material Symbols.
_ICONES_USADOS = "inventory_2,description,add,swap_horiz,delete,history,request_quote,download,search,insights,monitoring"
_FONTE_ICONES = (
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:"
    f"opsz,wght,FILL,GRAD@20,400,0,0&icon_names={_ICONES_USADOS}"
)

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
        align-items: center;
        gap: 0.85rem;
        border-bottom: 2px solid {COR_MARCA};
        padding-bottom: 0.7rem;
        margin-bottom: 1.4rem;
    }}
    .ctp-logo {{
        height: 42px;
        width: 42px;
        object-fit: cover;
        border-radius: 0.5rem;
        border: 1px solid {COR_BORDA};
        flex-shrink: 0;
    }}
    .ctp-marca {{
        color: {COR_MARCA};
        font-weight: 700;
        font-size: 1.375rem;
        letter-spacing: 0.01em;
    }}
    .ctp-subtitulo {{
        color: {COR_TEXTO_SECUNDARIO};
        font-size: 0.9375rem;
    }}

    .ctp-secao {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.0625rem;
        font-weight: 600;
        color: {COR_TEXTO};
        margin: 0 0 0.7rem 0;
    }}
    .ctp-secao .md-icon {{
        color: {COR_MARCA};
    }}

    /* cards: formulários e o container da coluna Excluir recebem a mesma
       superfície elevada sobre o fundo da página — sem isso cada seção era
       só uma caixa com borda fina genérica do Streamlit. `COR_SUPERFICIE`
       já vem certa pro tema ativo (branco no claro, navy-escuro no escuro). */
    div[data-testid="stForm"], [class*="st-key-card_"] {{
        background: {COR_SUPERFICIE};
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
        background: {COR_SUPERFICIE} !important;
    }}
    .st-key-card_excluir div[data-testid="stButton"] button:hover:not(:disabled) {{
        background: {COR_ERRO_FUNDO} !important;
    }}
    .st-key-card_excluir div[data-testid="stButton"] button:disabled {{
        border-color: {COR_BORDA} !important;
        color: {COR_TEXTO_MUTED} !important;
        background: {COR_SUPERFICIE} !important;
    }}

    /* painel "centro de controle" (só o gráfico da aba Análise) — sobrepõe
       o cartão claro genérico acima (mesmo seletor de prefixo, declarado
       depois: vence por ordem no CSS). Sombra colorida em vez de cinza
       neutra pra reforçar a sensação de painel iluminado. */
    [class*="st-key-card_escuro_"] {{
        background: {COR_ESCURO_FUNDO} !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 12px 32px rgba(2, 30, 58, 0.45), inset 0 0 0 1px rgba(255, 255, 255, 0.03) !important;
    }}
    [class*="st-key-card_escuro_"] .ctp-secao {{
        color: #ffffff;
    }}
    [class*="st-key-card_escuro_"] .ctp-secao .md-icon {{
        color: {COR_ESCURO_GLOW};
    }}
    .ctp-caption-escuro {{
        color: {COR_ESCURO_TEXTO_SECUNDARIO};
        font-size: 0.8125rem;
        margin: -0.4rem 0 0.9rem 0;
    }}
    .ctp-live-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: {COR_STATUS_AO_VIVO};
        box-shadow: 0 0 6px 2px rgba(161, 240, 31, 0.65);
        margin-right: 0.4rem;
        vertical-align: middle;
        animation: ctp-pulse 1.8s ease-in-out infinite;
    }}
    @keyframes ctp-pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.35; }}
    }}
    </style>
    <div class="ctp-header">
        <img class="ctp-logo" src="data:image/jpeg;base64,{base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")}" alt="Logotipo {MARCA}" />
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


aba_estoque, aba_cotacao, aba_analise = st.tabs(["Estoque", "Cotação", "Análise"])


def _status_saldo(saldo_kg: float) -> tuple[str, str, str]:
    """Classifica o saldo em 3 faixas de alerta visual (pedido explícito do
    dono do sistema): abaixo de 1kg = crítico (vermelho), de 1kg até 3kg =
    atenção (amarelo), acima de 3kg = adequado (verde). Nos limites exatos
    (1kg, 3kg) o saldo entra na faixa mais alta — 1kg conta como "atenção",
    não "crítico"; 3kg conta como "adequado", não "atenção". Devolve
    (rótulo, cor do texto, cor de fundo)."""
    if saldo_kg < LIMITE_CRITICO_KG:
        return "Crítico", COR_ERRO_TEXTO, COR_ERRO_FUNDO
    if saldo_kg < LIMITE_ATENCAO_KG:
        return "Atenção", COR_ATENCAO_TEXTO, COR_ATENCAO_FUNDO
    return "Adequado", COR_SUCESSO_TEXTO, COR_SUCESSO_FUNDO


def _tabela_filamentos(lista, incluir_kg=True):
    """DataFrame com o mesmo formato usado nas duas abas — datas e números
    formatados de forma consistente (mesmo separador de milhar dos KPIs,
    em vez de número cru)."""
    linhas = []
    for f in lista:
        saldo_kg = f["saldo_g"] / 1000
        linha = {
            "Material": f["material"],
            "Cor": f["cor"],
            "Saldo (g)": f["saldo_g"],
        }
        if incluir_kg:
            linha["Saldo (kg)"] = round(saldo_kg, 3)
        linha["Status"] = _status_saldo(saldo_kg)[0]
        linha["Cadastrado em"] = pd.to_datetime(f["criado_em"])
        linhas.append(linha)
    return pd.DataFrame(linhas)


def _colorir_por_status(row: pd.Series) -> list[str]:
    """Estilo de linha (pandas Styler) pra `st.dataframe` — toda a linha do
    filamento fica com o alerta de cor, não só a célula do saldo, pra ficar
    claro que é o filamento inteiro que está com estoque baixo."""
    _, cor_texto, cor_fundo = _status_saldo(row["Saldo (g)"] / 1000)
    return [f"background-color: {cor_fundo}; color: {cor_texto};"] * len(row)


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
                df_estoque.style.apply(_colorir_por_status, axis=1),
                hide_index=True,
                width="stretch",
                column_config={
                    "Saldo (g)": st.column_config.NumberColumn(format="%,.0f"),
                    "Saldo (kg)": st.column_config.NumberColumn(format="%,.2f"),
                    "Cadastrado em": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                },
            )
            st.caption(
                f"Crítico: abaixo de {LIMITE_CRITICO_KG:.0f}kg  •  "
                f"Atenção: de {LIMITE_CRITICO_KG:.0f}kg até {LIMITE_ATENCAO_KG:.0f}kg  •  "
                f"Adequado: acima de {LIMITE_ATENCAO_KG:.0f}kg"
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

# ============================================================ ANÁLISE ====
# Cor única nas barras (não uma cor por material): material é categoria
# nominal — a ordem não carrega significado — e o gráfico tem só uma série
# (saldo). Colorir cada barra de um jeito diferente gastaria o canal de
# identidade pra re-codificar o que o comprimento da barra já mostra sozinho
# (e exigiria legenda pra decodificar, sem necessidade: o rótulo já está no
# eixo). O "glow" é estético (tom mais claro da mesma família azul da marca),
# não outra cor de identidade — continua sendo uma cor fazendo um trabalho só.


def _grafico_estoque_por_material(dados_material: list[dict]):
    """Medidores horizontais (trilho + preenchimento), maior saldo no topo —
    estética de painel de controle pedida explicitamente pelo dono do
    sistema. Trilho = capacidade de referência (maior saldo entre os
    materiais); preenchimento = saldo real de cada um, azul-glow com ponta
    arredondada. Rótulo de valor sempre visível (não só no hover) — só 5-6
    categorias, cabe sem virar poluição. (Uma versão anterior também
    desenhava um marcador na ponta da barra pra reforçar o "glow" — removido
    porque colidia com o rótulo de valor, escondendo o primeiro dígito.)"""
    dados_ordenados = list(reversed(dados_material))  # maior valor no topo
    materiais = [d["material"] for d in dados_ordenados]
    saldos_kg = [d["saldo_g"] / 1000 for d in dados_ordenados]
    maior_kg = max(saldos_kg) if saldos_kg else 0
    capacidade = [maior_kg] * len(materiais)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=capacidade,
            y=materiais,
            orientation="h",
            marker=dict(color="rgba(255,255,255,0.08)", cornerradius=20),
            width=0.55,
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=saldos_kg,
            y=materiais,
            orientation="h",
            marker=dict(color=COR_ESCURO_GLOW, cornerradius=20),
            width=0.55,
            text=[f"{v:,.1f} kg" for v in saldos_kg],
            textposition="outside",
            textfont=dict(color="#ffffff", size=14, family="Inter, system-ui, sans-serif"),
            cliponaxis=False,
            hovertemplate="<b>%{x:,.2f} kg</b><br>%{y}<extra></extra>",
            showlegend=False,
        )
    )
    altura = 64 * len(materiais) + 40
    fig.update_layout(
        barmode="overlay",
        height=altura,
        margin=dict(l=10, r=70, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color="#ffffff", size=13),
        showlegend=False,
        hoverlabel=dict(bgcolor=COR_ESCURO_FUNDO, bordercolor=COR_ESCURO_GLOW, font=dict(color="#ffffff")),
        xaxis=dict(
            visible=False,
            range=[0, maior_kg * 1.22 if maior_kg else 1],
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#ffffff", size=14, family="Inter, system-ui, sans-serif", weight=600),
            ticksuffix="   ",
        ),
    )
    return fig


def _tabela_uso_medio(filamentos: list[dict], uso_por_id: dict) -> pd.DataFrame:
    """Uma linha por filamento. `Uso médio semanal (g)` já sai como texto
    pré-formatado (não um NumberColumn numérico): o `st.dataframe` desta
    versão do Streamlit renderiza NaN como o texto literal "None" dentro de
    NumberColumn (bug real, confirmado isolando o caso antes de escrever
    isto — não é specific do format string, acontece até sem `format=`) —
    então pra "sem base de cálculo" aparecer como "—" em vez de "None" pro
    usuário, formatamos a string aqui e a coluna vira texto simples."""
    linhas = []
    for f in filamentos:
        info = uso_por_id.get(f["id"])
        if info is None:
            media_str, base = "—", "Sem saída registrada"
        elif info["media_semanal_g"] is None:
            media_str, base = "—", "Histórico insuficiente (menos de 1 semana)"
        else:
            media_str = f"{info['media_semanal_g']:,.1f}"
            base = f"{info['semanas_historico']:.1f} semanas de histórico"
        linhas.append(
            {
                "Material": f["material"],
                "Cor": f["cor"],
                "Saldo atual (kg)": round(f["saldo_g"] / 1000, 3),
                "Uso médio semanal (g)": media_str,
                "Base de cálculo": base,
            }
        )
    return pd.DataFrame(linhas)


@st.fragment(run_every=INTERVALO_ATUALIZACAO_S)
def _painel_analise():
    """Todo o conteúdo da aba Análise roda como fragmento com
    auto-atualização — a cada `INTERVALO_ATUALIZACAO_S` segundos ele
    reconsulta o banco sozinho, sem recarregar o resto da página nem perder
    o que está preenchido nas outras abas. Assim, um lançamento feito por
    outra pessoa (ou outra aba do navegador) aparece aqui sem ação manual."""
    conn = conectar()
    saldo_material = [dict(m) for m in estoque.saldo_por_material(conn)]
    uso_por_id = estoque.uso_medio_semanal(conn)
    filamentos_analise = [dict(f) for f in estoque.listar_filamentos(conn)]
    conn.close()

    with st.container(key="card_escuro_grafico"):
        _titulo_secao("insights", "Estoque por material")
        st.markdown(
            f'<div class="ctp-caption-escuro"><span class="ctp-live-dot"></span>'
            f"Ao vivo — atualiza sozinho a cada {INTERVALO_ATUALIZACAO_S}s "
            f'(última leitura {datetime.datetime.now():%H:%M:%S})</div>',
            unsafe_allow_html=True,
        )
        if saldo_material:
            st.plotly_chart(
                _grafico_estoque_por_material(saldo_material),
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            st.markdown(
                '<div class="ctp-caption-escuro">Nenhum filamento cadastrado ainda.</div>',
                unsafe_allow_html=True,
            )

    with st.container(key="card_uso_medio"):
        _titulo_secao("monitoring", "Uso médio semanal por filamento")
        st.caption(
            "Média sobre todo o histórico de saídas registradas em "
            "\"Registrar entrada/saída\": total retirado dividido pelo "
            "número de semanas desde a primeira saída daquele filamento."
        )
        if not filamentos_analise:
            st.caption("Nenhum filamento cadastrado ainda.")
        else:
            busca_analise = st.text_input(
                "Buscar", placeholder="Filtrar por material ou cor…",
                label_visibility="collapsed", key="busca_analise", icon=":material/search:",
            )
            filtrados_analise = filamentos_analise
            if busca_analise.strip():
                alvo = busca_analise.strip().lower()
                filtrados_analise = [
                    f for f in filamentos_analise
                    if alvo in f["material"].lower() or alvo in f["cor"].lower()
                ]
            if filtrados_analise:
                st.dataframe(
                    _tabela_uso_medio(filtrados_analise, uso_por_id),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Saldo atual (kg)": st.column_config.NumberColumn(format="%,.2f"),
                    },
                )
            else:
                st.caption(f"Nenhum filamento bate com \"{busca_analise}\".")


with aba_analise:
    _painel_analise()
