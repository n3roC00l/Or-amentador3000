# Cotação de filamentos — agente + interface + exportação

## O que já está pronto e testado
- **Banco (`schema.sql` / `db.py`)**: SQLite como fonte de verdade. Testado.
- **Catálogo (`seed.py`)**: os 16 itens do seu arquivo atual, com as URLs de
  produto do 3DFILA (só ele tinha URL por item no arquivo original — 3DLAB
  e F3D saem sem URL, precisam ser cadastradas). Testado.
- **`export_excel.py`**: gera o Mapa de Cotação no layout do modelo atual.
  **A coluna "ORÇAMENTO MAIS ECONÔMICO" agora calcula o MIN de verdade** —
  testei forçando um caso onde a 3DLAB fica mais barata que a 3DFILA e a
  fórmula segue o preço corretamente, em vez de ficar presa na primeira
  coluna como no arquivo original. Rodei `recalc.py` do skill de xlsx:
  0 erros de fórmula.
- **F3D (`scrapers/f3d.py`)**: a loja expõe o preço numa meta tag própria
  (`nuvemshop:price`) — parser simples e confiável, confirmado contra a
  página real do produto.
- **Coletor (`collector.py`)**, **validação de faixa (`validacao.py`)** e
  **interface (`streamlit_app.py`)**: escritos e com sintaxe conferida, mas
  **não testados contra as lojas de verdade** — ver próxima seção.

## O que ainda precisa ser validado — e por quê
Este ambiente onde o código foi escrito não tem acesso de rede a lojas
externas (só a busca/leitura de texto via ferramentas do Claude, não a
requisições HTTP arbitrárias que os scrapers fazem). Isso significa:

1. **`scrapers/dfila.py` e `scrapers/lab3d.py` não foram testados contra o
   HTML bruto real.** A lógica foi desenhada em cima do padrão conhecido do
   WooCommerce (bloco `data-product_variations` com JSON de variantes), mas
   preciso que você rode:
   ```
   python -m scrapers.dfila https://3dfila.com.br/produto/filamento-pla-amarelo/
   python -m scrapers.lab3d https://3dlab.com.br/produto/filamento-pla-azul/
   ```
   e confira se o preço bate com o carrinho de verdade (peso 1kg). Se der
   `ErroColeta` dizendo que o bloco de variações não foi encontrado, o tema
   do site carrega isso via AJAX e o próximo passo é trocar para Playwright.

2. **Achei dois problemas de precisão reais nas lojas, documentados nos
   comentários de cada arquivo:**
   - **3DFila**: o preço "em destaque" da página é da variante mais barata
     (ex.: amostra de 75g pode aparecer como "a partir de R$5,90"), não do
     carretel de 1kg. Sem resolver a variante certa, o preço capturado
     seria completamente errado — por isso o parser falha explicitamente
     se não conseguir confirmar a variante de 1kg, em vez de arriscar.
   - **3D Lab**: tem desconto por volume que soma a quantidade de **todas
     as cores da mesma categoria** no carrinho — não dá pra saber isso
     olhando um produto isolado. O parser captura o preço unitário sem
     esse desconto e marca a leitura como `suspeito`, nunca `ok`, até
     alguém revisar.

3. **URLs de produto do 3DLAB e F3D não estão cadastradas** (o arquivo
   original só tinha por item para o 3DFILA). Sem URL, o coletor não tenta
   aquele fornecedor para aquele item — não existe "adivinhação" de
   produto. Posso ajudar a descobrir e confirmar essas URLs.

## Como rodar (na sua máquina, com rede de verdade)
```
pip install -r requirements.txt
python seed.py            # popula o catálogo (uma vez)
python collector.py       # roda a coleta de preços
streamlit run streamlit_app.py   # abre a interface de comparação/exportação
```

## Próximo passo sugerido
Rodar os dois comandos de validação do item 1 acima contra 1-2 produtos
reais e me trazer o resultado (ou o erro) — a partir disso eu ajusto o
parser certo em vez de ficar adivinhando a estrutura do HTML.
