# Guia de reformulação visual — Estoque e Cotação (Cilla Tech Park)

**Status:** implementado em 29/07/2026 (ver checklist no fim deste
arquivo). Regressão (`AppTest`) revalidada, conferência visual feita via
Chromium headless real (não só leitura de código).

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

| Papel | Cor | Uso |
|---|---|---|
| Marca (navy) | `#063a70` | ações primárias, header, destaque de marca — era `#2a78d6` |
| Marca escura | `#042c56` / `#021e3a` | hover/estados escuros (uso futuro, não crítico agora) |
| Destaque (lime) | `#a1f01f` | **só** indicadores de status/sucesso — nunca como cor de texto direta (contraste ruim em fundo claro), ver linha "Sucesso" abaixo |
| Fundo da página | `#e6ebf2` | fundo geral — era `#f6f8fb` |
| Superfície (card) | `#ffffff` | cards sobre o fundo — cria hierarquia sem sombra pesada |
| Fundo de input/muted | `#f6f8fb` / `#f4f7fa` | inputs, cabeçalho de tabela |
| Borda | `#e2e8f0` | bordas de card/input — era `#e2e6ee` |
| Texto primário | `#0a1628` | era `#1a1f2b` |
| Texto secundário | `#4b5769` | labels, legendas, captions |
| Texto desabilitado/muted | `#8898aa` | placeholders |
| **Sucesso** | `#3f6212` texto / `#d4f89e` fundo | confirmações — fundo é o `--ctp-lime-muted` real do site; texto é um tom escuro derivado do mesmo matiz (o lime puro `#a1f01f` não passa em contraste como texto — decisão do usuário foi "lime só em indicador de status/sucesso", então a família de cor muda pra lime, mas a legibilidade fica garantida com um verde-oliva escuro em vez do lime cru) |
| Atenção | `#a15c00` texto / `#fdf3e3` fundo | avisos — não fazia parte da paleta extraída, mantido |
| Erro | `#b3261e` texto / `#fdecea` fundo | erros — não fazia parte da paleta extraída, mantido |

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
- [x] Paleta alinhada ao Espaço Maker CTP (navy `#063a70` + lime `#a1f01f` em sucesso/status) — `config.toml`, `streamlit_app.py`, `DESIGN.md` atualizados; regressão revalidada, conferência visual do navy feita via Chromium headless (sucesso/lime não capturado no screenshot por causa do `st.rerun()` logo depois — mesmo mecanismo de tema já confirmado funcionando no alerta de erro)
