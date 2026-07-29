# Guia de reformulação visual — Estoque e Cotação (Cilla Tech Park)

**Status:** implementado em 29/07/2026 (ver checklist no fim deste
arquivo). Regressão (`AppTest`) revalidada, conferência visual feita via
Chromium headless real (não só leitura de código).

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

Fundo neutro frio (cinza-azulado, não bege/quente), cor de marca mantida:

| Papel | Cor | Uso |
|---|---|---|
| Marca | `#2a78d6` | ações primárias, links, destaque de marca |
| Fundo da página | `#f6f8fb` | fundo geral |
| Superfície (card) | `#ffffff` | cards sobre o fundo — cria hierarquia sem sombra pesada |
| Borda | `#e2e6ee` | bordas de card/input |
| Borda forte | `#c9d0dc` | divisórias, cabeçalho de tabela |
| Texto primário | `#1a1f2b` | mantido |
| Texto secundário | `#5b6472` | labels, legendas, captions |
| Texto desabilitado | `#98a1b0` | placeholders |
| Sucesso | `#1a8754` texto / `#eaf6ef` fundo | confirmações |
| Atenção | `#a15c00` texto / `#fdf3e3` fundo | avisos |
| Erro | `#b3261e` texto / `#fdecea` fundo | erros — não o vermelho "alarme" padrão do Streamlit |

Cores semânticas entram via `theme.redColor`/`greenColor`/`orangeColor` no
`.streamlit/config.toml` — o Streamlit deriva sozinho os fundos/tons de
`st.error`/`st.success`/`st.warning`/`st.info`.

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
- Ícones via Google Fonts (CDN) — mesma dependência de rede que o próprio
  Streamlit já tem hoje; a query pode ser restrita só aos ícones usados.
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
