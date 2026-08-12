# Estoque e Cotação de Filamentos — Cilla Tech Park

## Avatar fixo, independente da barra lateral (12/08/2026)

Pedido do dono do sistema: o avatar (foto de perfil) sumia quando a
barra lateral era fechada, porque vivia dentro dela. Movido pra fora do
`with st.sidebar:` em `streamlit_app.py` e fixado no canto superior
esquerdo via CSS (`position: fixed`, classe `.ctp-avatar-fixo`) — motivo
de ficar fora da sidebar no Python, não só no CSS: o Streamlit anima
recolher/abrir a barra com `transform` no contêiner dela, e qualquer
elemento `fixed` que esteja DENTRO de um ancestral com `transform` passa
a se posicionar relativo a esse ancestral (regra do CSS), não ao viewport
— ou seja, deslizaria escondido junto com a barra em vez de continuar
visível. Posição exata (`top`/`left`) é uma estimativa inicial, sem
navegador real pra conferir pixel a pixel — pode precisar de ajuste fino
depois de um print de tela.

## Bug visual real: texto de ícone sobreposto (12/08/2026, achado por print de tela)

Dono do sistema reportou "bugs de formatação" no canto da tela, com print
real do Firefox. Achado: texto tipo "LOGOUT" sobreposto ao botão "Sair",
"ARROW_DOWNWARD" sobreposto a "Histórico de movimentações", "UPLOAD"
sobreposto a "Browse files" do upload de foto, e texto ilegível no menu
nativo "☰" → tema. Causa raiz (não um bug isolado por botão): o app
carregava via Google Fonts um subconjunto próprio da fonte "Material
Symbols Rounded" — mas o Streamlit já embute uma fonte com **esse mesmo
nome exato**, localmente. Duas fontes disputando o mesmo `font-family` no
navegador — a nossa (só com os ícones que a gente lembrou de listar)
vencia até para ícones que o PRÓPRIO Streamlit desenha sozinho (seta do
expander, ícone do uploader, ícones do menu de tema), que então caíam no
fallback de mostrar o nome do ícone como texto puro. Corrigido em
`streamlit_app.py`: removido o `@import` próprio, `.md-icon` agora usa a
mesma fonte que o Streamlit já carrega (arquivo local completo, sem
subconjunto) — ver nota em `DESIGN.md` § Ícones. Não pego por teste
automatizado (`AppTest` não confere fonte/CSS) — só apareceu num print de
tela real.

## Aba Administração — contas de usuário no banco, não mais em arquivo (12/08/2026)

Pedido do dono do sistema (usuário `admin`) logo depois da hospedagem na
rede (seção abaixo): administrar as contas de acesso pela própria tela em
vez de editar `secrets.toml` na mão.

- **Credenciais saíram do `secrets.toml` e foram pro SQLite** — tabelas
  `usuarios` e `acessos` novas em `schema.sql`. Motivo: arquivo estático
  não dá pra "cadastrar" ou "editar" em runtime. Migração é automática e
  silenciosa: `auth.seed_inicial()` roda uma vez (a tabela `usuarios`
  nasce vazia) e recria as duas contas que já estavam em produção
  (`admin`/`pretomacaco`), então ninguém precisou recadastrar senha no dia
  da mudança. Senha nunca fica em texto puro — hash PBKDF2-HMAC-SHA256 com
  salt por conta (`auth.py`, só biblioteca padrão do Python, sem
  dependência nova).
- **Aba "Administração"** — só aparece em `st.tabs` pra quem loga com
  `papel = 'admin'` (mesmo princípio de "esconder o que não se aplica" já
  usado no resto do app). Mostra a lista de contas (usuário, papel, se tem
  foto, criado em, último acesso), um formulário pra cadastrar gente nova,
  um card pra editar qualquer conta (usuário, senha, papel, foto) e um
  histórico de logins. Uma trava: não dá pra tirar o papel `admin` da
  única conta administradora restante — sem isso um clique errado no
  formulário trancaria todo mundo fora do próprio painel de administração,
  sem jeito de desfazer pela interface.
- **Usuário comum** (ex.: `pretomacaco`) não vê a aba Administração — só
  ganha, na barra lateral, a opção de trocar a própria foto de perfil
  (JPG/PNG, até 3MB). É o único self-service liberado pra quem não é
  admin; tudo mais (renomear, trocar senha, virar admin) só o
  administrador faz, pela aba.
- Fotos ficam em `perfis/<id_do_usuário>.<extensão>` (fora do git — dado
  pessoal, mesmo raciocínio já usado pra não versionar `cotacoes.db`).
  Nome pelo id (não pelo nome de usuário) pra continuar valendo mesmo se a
  conta for renomeada depois.
- **Limitação conhecida**: se o admin edita uma conta que já está logada
  em outra aba/aparelho, quem está com a sessão aberta só vê a mudança
  (nome, papel, foto) depois de logar de novo — a sessão guarda os dados
  da conta em memória enquanto a aba do navegador ficar aberta, não
  reconsulta o banco a cada clique.

## Hospedagem na rede local e login (12/08/2026)

Pedido do dono do sistema: deixar o app hospedado rodando pra rede, não só
`localhost`. Resolve os itens 1 e 2 da lista de pendências críticas
registrada em 29/07/2026 (abaixo) — os outros dois (SQLite concorrente,
autoria nas movimentações) continuam em aberto.

- **Rede**: `.streamlit/config.toml` ganhou `[server]` com
  `address = "0.0.0.0"` (escuta em todas as interfaces, não só localhost) e
  `headless = true` (não tenta abrir aba de navegador local nem trava
  esperando o prompt de e-mail de primeiro uso — sem sentido rodando como
  serviço em segundo plano). Porta padrão mantida (`8501`). Acesso de
  qualquer aparelho na mesma rede/Wi-Fi: `http://192.168.30.250:8501` (IP
  da máquina onde o serviço roda — muda se a máquina trocar de rede/DHCP
  atribuir outro IP).
- **Login**: antes o app não tinha nenhuma barreira — virou risco real ao
  sair de `localhost`. Adicionada tela de usuário/senha em
  `streamlit_app.py` (função `_autenticar`, logo após `st.set_page_config`)
  — bloqueia toda a tela (`st.stop()`) até autenticar, com botão "Sair" na
  barra lateral. É uma senha por pessoa (não uma senha única
  compartilhada). Nessa rodada inicial as credenciais ficaram em
  `.streamlit/secrets.toml`; migraram pro banco (tabela `usuarios`, geridas
  pela aba Administração) na rodada seguinte no mesmo dia — ver seção
  acima. Ainda não guarda quem fez qual movimentação no estoque (a conta
  logada não é gravada em `movimentos_estoque`) — isso seria o próximo
  passo pra resolver o item 4 da lista de pendências (autoria).
- **Serviço systemd** (`~/.config/systemd/user/cotacao-filamentos.service`):
  roda `streamlit run streamlit_app.py` em segundo plano, reinicia sozinho
  se cair (`Restart=on-failure`) e sobe automaticamente no boot — habilitado
  via `systemctl --user enable --now`, com `loginctl enable-linger nero`
  pra iniciar mesmo sem sessão de usuário logada na máquina. Comandos úteis
  em "Como rodar" mais abaixo.
- **Só rede local, de propósito** — nada de port forwarding ou exposição pra
  internet pública nessa rodada (decisão explícita do dono do sistema:
  simplicidade e superfície de ataque menor pesaram mais que acesso remoto).
  O Streamlit loga uma "External URL" ao iniciar (IP público da rede) —
  isso é só o Streamlit detectando o IP, não significa que o app está
  alcançável de fora; sem regra de port forward no roteador, ele não está.
- **Validado** com `streamlit.testing.v1.AppTest` (mesmo mecanismo de teste
  já usado no projeto): tela de login aparece sem autenticação, credencial
  errada mostra erro e não libera acesso, os dois usuários cadastrados
  autenticam e liberam as três abas. Teste em navegador real não foi
  possível nesta rodada (extensão Claude in Chrome não estava conectada) —
  vale um clique manual de conferência.

## Aba Análise, alerta de saldo por cor, tema escuro e logotipo (10-12/08/2026)

Sequência de pedidos do dono do sistema. Resumo (detalhe de paleta e
contraste em `DESIGN.md`):

- **Aba Análise**: gráfico de estoque por material (painel escuro "centro
  de controle", atualiza sozinho a cada 15s via `st.fragment`) e tabela de
  uso médio semanal por filamento — calculado sobre o histórico de saídas
  (`estoque.uso_medio_semanal`), fica vazia até haver saída registrada em
  vez de mostrar "0" enganoso.
- **Alerta de saldo por cor** na tabela da aba Estoque: linha inteira em
  vermelho/amarelo/verde conforme o saldo (< 1kg / 1-3kg / > 3kg),
  reaproveitando as cores semânticas já usadas em erro/atenção/sucesso.
- **Tema escuro**: opção no menu nativo do Streamlit ("☰" → Settings →
  Theme). Substitui o tema fixo em claro que existia desde 29/07/2026.
- **Logotipo** da empresa no cabeçalho (`logo.jpg`).

Dois bugs reais encontrados e corrigidos durante o trabalho: `st.dataframe`
mostrava o texto literal "None" em vez de célula em branco pra valores
ausentes em colunas numéricas formatadas (contornado virando a coluna em
texto pré-formatado); e um marcador decorativo no gráfico da aba Análise
sobrepunha o primeiro dígito do rótulo de valor (removido).

## Reformulação visual completa (29/07/2026, fim de tarde)

Pedido explícito: zero emoji, hierarquia tipográfica real, cards com
anatomia clara, tabelas com contraste, alertas integrados à paleta — cara
de sistema corporativo de fábrica/parque tecnológico, não protótipo
genérico de Streamlit. Plano completo (paleta, tipografia, ícones,
layout) e checklist de implementação em **[`DESIGN.md`](DESIGN.md)** —
aprovado antes de implementar, atualizado conforme cada item foi
concluído.

Resumo do que mudou: tema claro com paleta neutra fria (não bege, não
preto) via `.streamlit/config.toml`, tipografia Inter com escala de papéis
definida, ícones Material Symbols Rounded (nativos via `icon=` em botão/
expander/alerta, e via HTML+CSS nos títulos de seção — `st.tabs` não
aceita HTML nem `icon=`, então as abas ficaram só com texto, decisão
documentada no `DESIGN.md`), cards com superfície branca elevada sobre o
fundo cinza da página, botão "Excluir" tratado como ação destrutiva
(vermelho, não azul de marca), e as cores de `st.error`/`st.success`/
`st.warning` recalibradas pra paleta do sistema em vez do vermelho/amarelo
padrão do Streamlit. Regressão (`AppTest`) revalidada e conferência visual
feita via Chromium headless real.

## Revisão de qualidade e identidade visual (29/07/2026, à tarde)

Pedido do dono do sistema: revisão como engenheiro de software pensando em
uso corporativo multiusuário, e interface com cara profissional (não a
aparência padrão de app Streamlit de protótipo).

**Bugs reais encontrados e corrigidos:**
- **Duplicidade silenciosa**: `estoque.adicionar_filamento` cadastrava um
  novo filamento mesmo quando material+cor já existia — testei ao vivo
  ("PLA Azul" duas vezes virava duas linhas, 1850g e 500g, em vez de uma
  só com 2350g). Corrigido: agora casa por material+cor (sem diferenciar
  maiúscula/espaço nas pontas) e, se já existe, **mescla** — registra a
  quantidade nova como entrada no cadastro existente em vez de duplicar.
  Interface avisa "já existia — mesclado" nesse caso.
- **Botão "Excluir" sem barreira no código** (achado na rodada de teste
  anterior): só dependia do atributo visual `disabled` do Streamlit.
- **Toolbar de desenvolvedor exposta**: o menu "⋮"/"Deploy" do Streamlit
  (chrome de ambiente de dev) aparecia pra qualquer usuário. Escondido via
  `.streamlit/config.toml` (`toolbarMode = "minimal"`).
- **Formatação inconsistente**: KPIs mostravam separador de milhar e as
  tabelas não (ou usavam convenção diferente entre si). Padronizado em
  toda a tela. Datas passaram de timestamp ISO cru
  (`2026-07-29T14:09:52`) para `29/07/2026 14:09`.

**Identidade visual:** tema claro fixo com a cor da marca (`#2a78d6`) via
`.streamlit/config.toml` — não muda com o SO/tema de quem abre, pra manter
a marca consistente pra todo mundo que acessar. Seções da aba Estoque
viraram cards com ícone (➕ Adicionar, 🔁 Registrar, 🗑️ Excluir, 🕘
Histórico) em vez de colunas soltas com texto em negrito.

**Adicionado:** campo de busca/filtro (por material ou cor) nas duas abas
— sem isso, um catálogo maior de filamentos vira uma lista rolável sem
jeito de achar nada rápido.

Validado com testes automatizados (`streamlit.testing.v1.AppTest`,
cobrindo mesclagem de duplicata, busca, movimentação e exclusão) e
conferido visualmente com screenshots reais via Chromium headless (não só
leitura de código) — inclusive num viewport de celular (430px), pra
checar que as colunas não quebram feio em tela estreita.

**Ficou de fora desta rodada, de propósito** (pedido explícito do dono:
"resolva os bugs de qualidade primeiro") — são os 4 pontos "críticos" da
revisão de engenharia que motivou essa rodada, ainda pendentes:
1. **Sem autenticação** — qualquer um com o link vê/edita/exclui o estoque
   de todo mundo.
2. **Só roda em `localhost`** — ninguém fora desta máquina acessa ainda;
   falta um deploy real.
3. **SQLite não aguenta bem escrita concorrente de várias pessoas** ao
   mesmo tempo — ok pra 1 usuário, ponto de estrangulamento real num
   "sistema corporativo" de verdade.
4. **Sem registro de autoria** nas movimentações (`motivo` é texto livre,
   não há campo "quem fez").

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

## Como rodar

**Hospedado na rede (já configurado, ver seção acima)** — o app roda como
serviço systemd na máquina `192.168.30.250`, sobrevive a reboot e reinicia
sozinho se cair. Acesse de qualquer aparelho na mesma rede:
`http://192.168.30.250:8501` (login com usuário/senha — contas geridas na
aba Administração por quem tiver papel de admin).

Comandos úteis nessa máquina:
```
systemctl --user status cotacao-filamentos    # ver se está rodando
systemctl --user restart cotacao-filamentos   # aplicar mudança de código/config
journalctl --user -u cotacao-filamentos -f    # acompanhar log em tempo real
```

**Rodando manualmente (desenvolvimento/depuração)**
```
pip install -r requirements.txt
streamlit run streamlit_app.py   # abre a interface de estoque e cotação
```
