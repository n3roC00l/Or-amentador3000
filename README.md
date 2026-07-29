# Estoque e Cotação de Filamentos — Cilla Tech Park

## O que já está pronto e testado (29/07/2026)

**Mudança de rumo nesta data:** o fluxo deixou de ser "raspar as 3 lojas e
comparar preço automaticamente" e passou a ser **controle de estoque
próprio + pedido de cotação manual**. O motivo: o dono do sistema não quer
mais que o software decida sozinho quem é mais barato — quer saber quanto
tem guardado e, quando precisar comprar, gerar uma lista pra mandar pras
3 empresas cotarem de verdade.

- **`schema.sql`**: duas tabelas novas, `filamentos` (catálogo dos tipos
  que você decide rastrear — material + cor, não vem de raspagem de loja)
  e `movimentos_estoque` (histórico de entrada/saída em gramas). O saldo
  atual nunca é uma coluna solta — é sempre a soma do histórico, mesmo
  princípio de "nunca sobrescreve" que o sistema já usava para preço.
- **`estoque.py`**: lógica de negócio — adicionar/excluir filamento,
  registrar entrada/saída, calcular saldo e ver histórico. Testado direto
  (sem interface) simulando um ciclo completo: adicionar 1000g → saída
  300g → entrada 200g → saldo final 900g confere, exclusão remove
  filamento e histórico junto.
- **`relatorio_cotacao.py`**: gera o pedido de cotação em Excel (lista
  simples: item, material, cor, quantidade necessária — **sem** coluna de
  preço, porque isso é a empresa quem preenche na resposta). Levanta erro
  se a lista vier vazia, não gera planilha em branco.
- **`streamlit_app.py`**: interface com duas abas, testada de ponta a
  ponta via `streamlit.testing.v1.AppTest` (roda o app de verdade, sem
  navegador) e checagem direta no banco antes/depois de cada ação:
  - **📦 Estoque**: tabela com saldo atual de cada filamento (g e kg),
    formulário de adicionar (material + cor + quantidade inicial),
    formulário de registrar entrada/saída (com motivo), exclusão com
    checkbox de confirmação, e histórico de movimentações por filamento.
  - **📋 Cotação**: tabela editável (`st.data_editor`) pra marcar quais
    filamentos precisa comprar e quanto; gera o Excel do pedido só com os
    itens marcados **e** com quantidade > 0 (testado o filtro isolado —
    item marcado sem quantidade, ou com quantidade mas não marcado, fica
    de fora). Botão de gerar avisa em vez de travar se nada foi
    selecionado.
  - **Bug real encontrado e corrigido durante o teste**: o botão
    "Excluir" só ficava bloqueado pelo atributo visual `disabled` do
    Streamlit (que impede o clique no navegador, mas não é uma barreira
    no código). Adicionei checagem explícita de `confirmar` no `if` do
    botão — agora a exclusão exige a confirmação nos dois níveis, não só
    na interface.
  - **Limitação conhecida do teste**: `st.data_editor` não é
    simulável por `AppTest` nesta versão do Streamlit (sem suporte a
    editar célula programaticamente) — a lógica de filtro downstream
    (seleção + quantidade > 0 → gera relatório) foi validada isolada com
    um DataFrame sintético reproduzindo exatamente a saída esperada do
    editor, mas a interação real de marcar checkbox/digitar quantidade
    na grade não passou por teste automatizado. Vale um clique manual
    de conferência.

## O que ficou dormente (fluxo antigo de cotação ao vivo)

`fornecedores`, `itens`, `urls_produto`, `cotacoes` (schema), `db.py`
(funções ligadas a essas tabelas), `collector.py`, `validacao.py`,
`export_excel.py` e os scrapers em `scrapers/` (`f3d.py`, `dfila.py`,
`lab3d.py`) continuam no repositório e funcionam via linha de comando —
não foram apagados porque têm histórico real de preço coletado nas 3
lojas em 28/07/2026, útil como referência. Só não são mais chamados pela
interface principal. Pra reativar esse fluxo: `python collector.py` +
`python export_excel.py` continuam rodando como antes.

## O que ainda falta revisar

1. **Testar a aba Cotação com clique real no navegador** — a interação
   com `st.data_editor` (marcar checkbox, digitar quantidade) não foi
   coberta por teste automatizado (ver limitação acima).
2. Não há histórico persistido de *pedidos de cotação já enviados* — cada
   geração de Excel é um evento avulso, não fica salvo no banco quem foi
   pedido quando. Se isso importar (ex.: "já pedi cotação desse item mês
   passado?"), é a próxima peça a desenhar.
3. `material` no formulário de adicionar filamento é uma lista fixa (PLA,
   PETG, ABS, TPU, ASA, HIPS, Nylon, PC, Outro) com campo livre pra
   "Outro" — se aparecer material recorrente fora dessa lista, vale
   adicionar na lista fixa pra evitar grafia inconsistente.

## Como rodar (na sua máquina)
```
pip install -r requirements.txt
streamlit run streamlit_app.py   # abre a interface de estoque e cotação
```
