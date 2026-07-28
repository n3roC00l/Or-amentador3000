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
- **`validacao.py`** e **`streamlit_app.py`**: sintaxe conferida; a lógica
  de faixa e a tabela de comparação foram exercitadas indiretamente pelo
  `collector.py` acima, mas a interface Streamlit em si ainda não foi
  aberta num navegador.

## O que ainda falta revisar
1. **Confirmar as URLs "aprox."** listadas nos comentários de `seed.py`
   (PLA Rosa no 3DLAB, PETG Azul/Laranja/Verde no 3DLAB, PETG Laranja no
   F3D) — são a cor mais próxima disponível, não a cor exata do catálogo
   original.
2. **3D Lab**: desconto por volume soma todas as cores da mesma categoria
   no carrinho — o preço capturado é sempre o unitário sem desconto,
   marcado `suspeito` de propósito. Validar contra um carrinho real antes
   de fechar compra.
3. **Abrir a interface** (`streamlit run streamlit_app.py`) e conferir a
   tabela de comparação e a exportação na prática, num navegador.
4. **Ajustar `faixa_min`/`faixa_max`** em `seed.py` — hoje são só um ponto
   de partida do arquivo antigo; os preços reais coletados (R$89-150 em
   PLA, R$89-146 em PETG) já dão uma calibração melhor.

## Como rodar (na sua máquina, com rede de verdade)
```
pip install -r requirements.txt
python seed.py            # popula o catálogo (uma vez)
python collector.py       # roda a coleta de preços
streamlit run streamlit_app.py   # abre a interface de comparação/exportação
```
