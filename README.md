# Cotação de filamentos — agente + interface + exportação

## O que já está pronto e testado (28/07/2026 — validado contra as 3 lojas de verdade)
- **Banco (`schema.sql` / `db.py`)**: SQLite como fonte de verdade. Testado.
- **Catálogo (`seed.py`)**: os 16 itens do arquivo original, agora com URL
  de produto cadastrada para os **3 fornecedores** (3DFILA, 3DLAB, F3D) —
  48 URLs no total, todas conferidas com HTTP 200 antes de cadastrar. Onde
  a loja não vende a cor exata do catálogo original, a URL mais próxima
  disponível foi marcada como "aprox." direto no comentário do arquivo
  (ex.: 3DLAB só tem "PETG UV translúcido", não PETG opaco, nas cores
  azul/laranja/verde) — revisar essas antes de confiar 100% no preço.
- **`scrapers/base.py`**: **bug real encontrado e corrigido** — o
  `User-Agent` tinha acentos (ç/ã/õ) e isso derrubava toda requisição pro
  3DLAB com 403 (WAF Cloudflare rejeita header com bytes não-ASCII).
  Confirmado lado a lado: mesma URL, mesmo texto, só tirando o acento já
  vira 200. Corrigido para ASCII puro.
- **Os 3 scrapers (`f3d.py`, `dfila.py`, `lab3d.py`)**: rodados de verdade
  contra páginas de produto reais das 3 lojas. `dfila.py` conferido byte a
  byte contra o JSON de variações bruto (variante 1kg = R$89,90, bate
  exato). `lab3d.py` também confirmado (variante 1kg encontrada, marcada
  `suspeito` como projetado, por causa do desconto por volume). `f3d.py`
  detecta corretamente produto sem estoque via `nuvemshop:stock=0`.
  **3DLAB tem rate-limiting intermitente (Cloudflare)** — rajadas de
  requisições levam a 403 esporádicos que passam a funcionar de novo
  segundos depois; o coletor não tem retry automático hoje, então uma
  falha pontual do 3DLAB no meio de uma coleta é esperada, não é bug.
- **`collector.py`**: rodado de ponta a ponta contra as 3 lojas reais com
  as 48 URLs — 0 falhas, 24 leituras `ok`, 24 `suspeito` (todo o 3DLAB por
  design + metade do F3D por falta de estoque sinalizada nesse momento).
- **`export_excel.py`**: gera o Mapa de Cotação no layout do modelo atual a
  partir de dados reais coletados. A coluna "ORÇAMENTO MAIS ECONÔMICO"
  calcula o MIN de verdade (testado com a 3DLAB ficando mais barata que a
  3DFILA em alguns itens de fato).
- **`validacao.py`**: sintaxe conferida; a lógica de faixa foi exercitada
  indiretamente pelo `collector.py` acima.
- **`streamlit_app.py` (interface "Cilla Tech Park")**: reformulada e
  aberta de verdade num navegador (Chromium headless via CDP) — testes
  visuais confirmaram cada peça abaixo funcionando com dados reais:
  - **Cotação ao vivo com cache de 15 min**: ao abrir a tela, se a última
    coleta salva tiver mais de `LIMITE_FRESCOR_MIN` (15 min), ela dispara
    `collector.coletar_tudo()` sozinha, com barra de progresso e log linha
    a linha (ver `st.status`). Um botão "🔄 Atualizar agora" força a busca
    a qualquer momento. Testado: rodou a coleta nas 3 lojas reais dentro da
    tela e o selo de status virou "🟢 atualizado agora mesmo" ao terminar.
  - **`collector.coletar_tudo(progress_callback=...)`**: agora aceita um
    callback de progresso (chamado a cada item/fornecedor processado) —
    é o que a interface usa para a barra ao vivo, em vez de rodar o
    coletor como subprocesso.
  - **Retry em cima do bloqueio intermitente do 3DLAB**: `collector.py`
    agora tenta de novo (até 2x) quando um scraper leva 403, e qualquer
    outro erro de rede vira `falha` numa linha só, em vez de derrubar a
    coleta inteira — corrige um bug real: antes, uma exceção de rede não
    tratada (`requests.exceptions.HTTPError`/`RequestException`) por fora
    de `ErroColeta` quebrava `coletar_tudo()` no meio do processamento.
  - **Único campo editável é a quantidade**: tabela via `st.data_editor`
    com todas as colunas travadas (`disabled=True`) exceto "Qtd". Editar
    grava direto em `itens.quantidade` (`db.atualizar_quantidade`) e
    recalcula o total na hora — **sem** disparar nova coleta (testado:
    editar quantidade não muda o selo "atualizado há X min", só o valor
    do total). `export_excel.py` já lê a quantidade do banco, então a
    planilha exportada reflete a edição automaticamente.
  - **Identidade visual "Cilla Tech Park"**: cabeçalho com a marca, selo de
    status colorido (🟢/🔵/🔴) e KPIs no topo (total mais econômico,
    leituras ok/suspeitas/sem preço), usando a paleta de status validada
    pela skill de dataviz (verde `#0ca30c` / amarelo `#fab219` / vermelho
    `#d03b3b`) em vez de cores escolhidas a dedo.

## O que ainda falta revisar
1. **Confirmar as URLs "aprox."** listadas nos comentários de `seed.py`
   (PLA Rosa no 3DLAB, PETG Azul/Laranja/Verde no 3DLAB, PETG Laranja no
   F3D) — são a cor mais próxima disponível, não a cor exata do catálogo
   original.
2. **3D Lab**: desconto por volume soma todas as cores da mesma categoria
   no carrinho — o preço capturado é sempre o unitário sem desconto,
   marcado `suspeito` de propósito. Validar contra um carrinho real antes
   de fechar compra.
3. **Ajustar `faixa_min`/`faixa_max`** em `seed.py` — hoje são só um ponto
   de partida do arquivo antigo; os preços reais coletados (R$89-150 em
   PLA, R$89-146 em PETG) já dão uma calibração melhor.

## Como rodar (na sua máquina, com rede de verdade)
```
pip install -r requirements.txt
python seed.py            # popula o catálogo (uma vez)
python collector.py       # roda a coleta de preços
streamlit run streamlit_app.py   # abre a interface de comparação/exportação
```
