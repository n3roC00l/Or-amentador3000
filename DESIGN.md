# Guia de reformulação visual — Estoque e Cotação (Cilla Tech Park)

**Status:** implementado em 29/07/2026 (ver checklist no fim deste
arquivo). Regressão (`AppTest`) revalidada, conferência visual feita via
Chromium headless real (não só leitura de código).

**Tema escuro + logotipo (12/08/2026):** pedido explícito do dono do
sistema. Até aqui o tema era fixo em claro, de propósito ("marca
consistente pra todo mundo que acessar" — nota histórica abaixo). Isso
mudou: o app agora define `[theme.light]`/`[theme.dark]` em
`.streamlit/config.toml` (mecanismo nativo do Streamlit, versão ≥ 1.4x — não
CSS customizado) e o usuário troca no menu nativo "☰" (canto superior
direito) → Settings → Theme, reexposto via `client.toolbarMode = "viewer"`
(mantém escondidos Deploy/Rerun/Clear cache, que foi o motivo original de
esconder o menu inteiro — ver seção "Revisão de qualidade" do README).
Como esse menu nativo só reflui os próprios widgets do Streamlit (botão,
campo, tabela), o CSS customizado deste app (cabeçalho, cards, ícones,
tabela de status) lê `st.context.theme.type` em Python e escolhe entre dois
dicionários de cor — sem isso cabeçalho/cards ficariam presos no claro
mesmo com o resto da tela em escuro. Cada cor escura foi conferida com o
validador de contraste da skill de dataviz contra o fundo `#0a1628` antes
de entrar (todas ≥ 4.5:1 — ver tabela "Paleta — par claro/escuro" abaixo).
**Limitação conhecida, não é bug nosso:** `st.context.theme.type` pode ficar
1 rerun atrasado logo após o usuário trocar de tema (documentado pelo
próprio Streamlit, [issue #11920](https://github.com/streamlit/streamlit/issues/11920))
— nesse intervalo os widgets nativos já mudaram mas o CSS customizado ainda
não; qualquer interação seguinte (trocar de aba, buscar) sincroniza.
Logotipo (`logo.jpg`, fornecido pelo usuário, copiado pra raiz do projeto)
embutido no cabeçalho via `data:` URI — fundo do arquivo já é o navy escuro
da marca, então funciona nos dois temas sem precisar de duas versões.

**Aba Análise + alerta de saldo por cor (10-12/08/2026):** também pedidos
explícitos do dono do sistema, ainda sem entrada própria neste guia —
registrados aqui por completude. Aba nova com gráfico de estoque por
material (painel escuro "centro de controle", fixo nesse estilo
independente do tema escolhido — é uma escolha visual deliberada, não seguiu
`_ESCURO`) e tabela de uso médio semanal; tabela da aba Estoque ganhou
alerta de cor por linha (vermelho/amarelo/verde conforme saldo, ver
`_status_saldo` em `streamlit_app.py`) reusando as cores semânticas de
erro/atenção/sucesso já documentadas abaixo.

**Aba Administração + avatar na barra lateral (12/08/2026):** também sem
entrada própria neste guia — registrado por completude. Reaproveita 100%
os componentes visuais já existentes (`_titulo_secao`, cartão via
`st.form`/`st.container(key=...)`, `st.dataframe` com `column_config` de
data): nenhuma cor, tipografia ou padrão de layout novo entrou por causa
dela. Único acréscimo visual real é o avatar circular pequeno
(`st.image`, 64px) no topo da barra lateral, mostrado só quando a conta
tem foto.

**Atualização de paleta (29/07/2026, à noite):** a paleta original abaixo
foi substituída pela paleta real do **Espaço Maker CTP**
(`espa-o-maker.vercel.app`) — outro sistema interno da Cilla Tech Park
(Demandas/Orçamentos/Estoque/Financeiro/Agenda), pra manter identidade
visual consistente entre as ferramentas internas da empresa. Extraída das
variáveis CSS reais do site (`:root`), não de leitura visual aproximada.
Ver tabela "Paleta" já atualizada com os valores novos; os antigos
(`#2a78d6` etc.) ficam só nesta nota como registro histórico.

**Um ajuste em relação ao plano original:** `st.tabs` não aceita HTML nem
o parâmetro `icon=` — só markdown limitado (negrito/itálico/links/imagem).
Simular o ícone via imagem exigiria recriar os glifos do Material Symbols
como SVG à mão, com risco real de sair visualmente errado. Optei por
deixar as abas só com texto ("Estoque", "Cotação") — ainda cumpre "zero
emoji", ícone fica em todo o resto (cards, botões, alertas, expander).

**Objetivo:** a lógica e os dados do sistema estão certos — o problema é só
visual. Hoje a interface parece um protótipo genérico do Streamlit; o
pedido é fazer parecer um sistema corporativo sério (fábrica/parque
tecnológico), sem virar o visual "genérico de IA" (nem bege+serifada+
terracota, nem preto quase puro+verde ácido).

Escopo é só visual — não muda nome de campo, fluxo ou a lógica de saldo
calculado a partir do histórico (`estoque.py`). Os testes de regressão em
`streamlit.testing.v1.AppTest` continuam valendo; se a reestruturação de
componentes exigir ajuste neles, o ajuste é parte do trabalho.

## Paleta

Fonte: variáveis CSS de `espa-o-maker.vercel.app` (Espaço Maker CTP),
extraídas via DevTools/computed style em 29/07/2026 — não é uma
aproximação visual, são os valores reais declarados no `:root` daquele
site.

A partir de 12/08/2026 cada papel tem par claro/escuro — o escuro não é uma
tradução mecânica do claro, foi escolhido e conferido contraste próprio
(ver nota "Tema escuro + logotipo" acima e `.streamlit/config.toml`).

| Papel | Cor (claro) | Cor (escuro) | Uso |
|---|---|---|---|
| Marca (navy/glow) | `#063a70` | `#3987e5` | ações primárias, header, destaque de marca — claro era `#2a78d6`; escuro precisa ser mais claro que o navy pra não sumir no fundo escuro |
| Marca escura | `#042c56` / `#021e3a` | — | hover/estados escuros no claro (uso futuro); no escuro `#021e3a` também é o fundo do painel "centro de controle" da aba Análise |
| Destaque (lime) | `#a1f01f` | `#a1f01f` (igual) | **só** indicadores de status/sucesso — nunca como texto direto no **claro** (contraste ruim em fundo claro); no escuro funciona até como texto (12.9:1), ver linha "Sucesso" |
| Fundo da página | `#e6ebf2` | `#0a1628` | fundo geral — claro era `#f6f8fb` |
| Superfície (card) | `#ffffff` | `#13233a` | cards sobre o fundo — cria hierarquia sem sombra pesada |
| Fundo de input/muted | `#f6f8fb` / `#f4f7fa` | `#17293f` | inputs, cabeçalho de tabela |
| Borda | `#e2e8f0` | `#24354c` | bordas de card/input — claro era `#e2e6ee` |
| Texto primário | `#0a1628` | `#f2f5f9` | claro era `#1a1f2b` |
| Texto secundário | `#4b5769` | `#b8c4d4` | labels, legendas, captions |
| Texto desabilitado/muted | `#8898aa` | `#5b7590` | placeholders |
| **Sucesso** | `#3f6212` texto / `#d4f89e` fundo | `#a1f01f` texto / `#1f2e0a` fundo | confirmações — claro: fundo é o `--ctp-lime-muted` real do site, texto é verde-oliva escuro (lime puro não passa em contraste como texto em fundo claro — decisão do usuário foi "lime só em indicador de status/sucesso"); escuro: lime puro funciona direto como texto |
| Atenção | `#a15c00` texto / `#fdf3e3` fundo | `#ffb84d` texto / `#3a2a10` fundo | avisos — claro não fazia parte da paleta extraída, mantido |
| Erro | `#b3261e` texto / `#fdecea` fundo | `#ff8a8a` texto / `#3a1518` fundo | erros — claro não fazia parte da paleta extraída, mantido |

Cores semânticas entram via `theme.redColor`/`greenColor`/`orangeColor` no
`.streamlit/config.toml` — o Streamlit deriva sozinho os fundos/tons de
`st.error`/`st.success`/`st.warning`/`st.info`.

Escala de raio disponível no site de referência (não adotada ainda, fica
registrada pra quando fizer sentido refinar): `sm` 6px, `md` 10px, `lg`
14px, `xl` 20px, `full` pill. Sombras lá são tingidas de navy em vez de
preto puro (`0 4px 12px #063a7014`) — mesmo princípio que já seguimos com
a sombra sutil dos cards, só não com a cor exata deles ainda.

## Tipografia

Fonte: **Inter** (Google Fonts, fallback `system-ui, sans-serif`) — números
tabulares, family comum em dashboard corporativo/B2B, não é a serifada
"genérica de IA" nem mono de dev tool.

| Papel | Tamanho | Peso | Cor |
|---|---|---|---|
| Marca (app) | 22px | 700 | marca |
| Subtítulo do app | 15px | 400 | texto secundário |
| Título de seção/card | 17px | 600 | texto primário |
| Rótulo de cabeçalho de tabela | 13px, versalete + letter-spacing | 600 | texto secundário |
| Dado de tabela / corpo | 14px | 400 | texto primário, numérico tabular |
| Valor de KPI | 28px | 700 | texto primário, numérico tabular |
| Legenda/estado vazio | 13px | 400 | texto secundário |

KPI menor que o padrão do Streamlit (28px vs 36px) — painel operacional
denso, não número de vitrine.

## Ícones

Zero emoji. **Material Symbols (Rounded)** — ícones de linha, aceitos
nativamente pelo Streamlit via `icon=":material/nome:"` em botão, expander
e nas caixas de erro/sucesso/aviso/info. Abas e títulos de seção (sem
parâmetro nativo) recebem o mesmo ícone via HTML+CSS pequeno, carregando a
mesma fonte — um único sistema de ícone em toda a tela.

| Hoje (emoji) | Ícone novo |
|---|---|
| 📦 Estoque | `inventory_2` |
| 📋 Cotação | `description` |
| ➕ Adicionar | `add` |
| 🔁 Registrar entrada/saída | `swap_horiz` |
| 🗑️ Excluir | `delete` |
| 🕘 Histórico | `history` |
| 📤 Gerar pedido | `request_quote` |
| ⬇️ Baixar | `download` |
| (busca, sem ícone hoje) | `search` |

**Correção de bug real (12/08/2026):** o plano original abaixo carregava
via Google Fonts (`@import`) só o subconjunto de glifos "realmente
usados" — intenção certa (baixar menos), execução com um problema sério:
o Streamlit já embute a própria fonte **com o mesmo nome exato**
("Material Symbols Rounded", conferido no CSS estático dele). Duas
declarações `@font-face` para o mesmo nome competem no navegador: a nossa
(subset) vencia, e qualquer ícone que o PRÓPRIO Streamlit usa
internamente fora da nossa lista — a seta de expandir/recolher do
`st.expander`, o ícone de upload do `st.file_uploader`, ícones do menu
nativo "☰" → tema — caía no fallback de fonte, que mostra o nome do ícone
como texto puro sobreposto ao rótulo real. Encontrado por print de tela
real no Firefox (não aparecia em teste automatizado, que não confere
fonte/CSS). Corrigido removendo o `@import` próprio e apontando `.md-icon`
pra a mesma fonte que o Streamlit já carrega (arquivo local, conjunto
completo, sem restrição) — resolve pros dois lados sem lista pra manter.

## Layout / componentes

- **Cards**: fundo branco sobre página cinza-clara, borda 1px + sombra
  sutil (`0 1px 2px rgba(16,24,40,.04)`), cabeçalho interno com
  ícone+título separado do conteúdo por linha fina.
- **Tabelas**: cabeçalho com fundo tintado e texto em versalete (via
  `dataframeHeaderBackgroundColor`/`dataframeBorderColor` do tema);
  números já alinham à direita por padrão do `NumberColumn`.
- **Botão Excluir**: tratado como ação destrutiva (contorno/texto na cor
  de erro), separado visualmente da ação principal — convenção padrão
  contra clique acidental.
- **Header do app**: mesma estrutura, nova escala tipográfica, borda
  inferior mais fina (2px em vez de 3px).

## Riscos técnicos conhecidos

- `st.dataframe`/`st.data_editor` renderiza célula via canvas, não HTML —
  o que o tema do Streamlit expõe (fonte geral, cor de cabeçalho, borda) dá
  pra controlar; refinamento fino dentro da grade pode ter limite.
- ~~Ícones via Google Fonts (CDN)~~ — removido em 12/08/2026: causava
  colisão de `font-family` com a fonte que o próprio Streamlit já embute
  localmente (ver nota na seção Ícones). Hoje não há dependência de CDN
  pros ícones — só a fonte local do Streamlit.
- Testes `AppTest` usam `label`, não estilo, então não devem quebrar com
  isso — reconferir de qualquer forma após qualquer mudança estrutural.

## Checklist de implementação

- [x] Paleta e tipografia via `.streamlit/config.toml` (theme tokens)
- [x] Ícones nativos (`:material/nome:`) em botões, expander, alertas
- [x] Ícones via HTML+CSS em títulos de seção (abas ficaram só texto — ver nota de status acima)
- [x] Cards com cabeçalho separado (ícone + título, superfície branca com sombra sutil)
- [x] Tabelas com cabeçalho tintado/contraste (`dataframeHeaderBackgroundColor`)
- [x] Botão "Excluir" com tratamento de ação destrutiva (contorno/texto vermelho, não azul de marca)
- [x] Header do app com nova escala tipográfica
- [x] Suíte de regressão (`AppTest`) revalidada após as mudanças
- [x] Conferência visual real (screenshots) antes/depois, incluindo alerta de erro com a paleta muted
- [x] Paleta alinhada ao Espaço Maker CTP (navy `#063a70` + lime `#a1f01f` em sucesso/status) — `config.toml`, `streamlit_app.py`, `DESIGN.md` atualizados; regressão revalidada, conferência visual do navy feita via Chromium headless (sucesso/lime não capturado no screenshot por causa do `st.rerun()` logo depois — mesmo mecanismo de tema já confirmado funcionando no alerta de erro)
- [x] Tema escuro completo (`[theme.light]`/`[theme.dark]` no `config.toml` + `st.context.theme.type` no CSS customizado) — todas as cores do escuro validadas por contraste antes de entrar; conferido ao vivo trocando de tema via Chromium headless (claro→escuro→claro), inclusive o atraso de 1 rerun documentado pelo Streamlit
- [x] Logotipo (`logo.jpg`) no cabeçalho, funciona nos dois temas sem versão separada (fundo do arquivo já é o navy escuro da marca)
- [x] Menu nativo "☰" reexposto via `toolbarMode = "viewer"` só pra alcançar o seletor de tema — Deploy/Rerun/Clear cache continuam escondidos
