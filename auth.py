"""
Contas de acesso ao sistema — autenticação, cadastro/edição de usuário e
foto de perfil. Guarda a mesma linha de `estoque.py`: funções livres que
recebem `sqlite3.Connection`, sem ORM, e levantam `ValueError` em erro de
validação pra interface transformar em `st.error`.

Senha nunca fica em texto puro: PBKDF2-HMAC-SHA256 com salt aleatório por
conta (stdlib, sem dependência nova). Foto de perfil vai pra `perfis/<id>.
<extensão>` (fora do git — dado pessoal) e só o nome do arquivo fica no
banco.
"""
import datetime
import hashlib
import secrets
import sqlite3
from pathlib import Path

PASTA_FOTOS = Path(__file__).parent / "perfis"
EXTENSOES_PERMITIDAS = ("jpg", "jpeg", "png")
TAMANHO_MAXIMO_FOTO = 3 * 1024 * 1024  # 3MB — evita upload gigante por engano
_ITERACOES_HASH = 200_000


def _hash_senha(senha: str, salt_hex: str | None = None) -> tuple[str, str]:
    """Devolve (hash_hex, salt_hex). Gera salt novo se não vier um
    existente (cadastro); reaproveita o salt salvo pra conferir senha no
    login."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, _ITERACOES_HASH)
    return hash_bytes.hex(), salt.hex()


def autenticar(conn: sqlite3.Connection, nome_usuario: str, senha: str) -> sqlite3.Row | None:
    """Confere usuário/senha. Em caso de sucesso, registra o acesso em
    `acessos` (pra aba Administração mostrar histórico) e devolve a conta;
    senão devolve None. `compare_digest` evita vazar por timing se o hash
    bate parcialmente."""
    linha = conn.execute(
        "SELECT * FROM usuarios WHERE nome_usuario = ?", (nome_usuario,)
    ).fetchone()
    if linha is None:
        return None

    hash_calculado, _ = _hash_senha(senha, linha["senha_salt"])
    if not secrets.compare_digest(hash_calculado, linha["senha_hash"]):
        return None

    agora = datetime.datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO acessos (usuario_id, logado_em) VALUES (?, ?)", (linha["id"], agora)
    )
    conn.commit()
    return linha


def buscar_usuario_por_id(conn: sqlite3.Connection, usuario_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()


def listar_usuarios(conn: sqlite3.Connection):
    """Cada conta + `ultimo_acesso` (None se nunca logou) — alimenta a
    tabela "Contas de acesso" da aba Administração."""
    return conn.execute("""
        SELECT u.*, MAX(a.logado_em) AS ultimo_acesso
        FROM usuarios u
        LEFT JOIN acessos a ON a.usuario_id = u.id
        GROUP BY u.id
        ORDER BY u.nome_usuario
    """).fetchall()


def historico_acessos(conn: sqlite3.Connection, limite: int = 50):
    """Últimos logins, mais recente primeiro — histórico completo fica na
    tabela `acessos` pra quem quiser auditar mais que `limite`."""
    return conn.execute("""
        SELECT a.logado_em, u.nome_usuario
        FROM acessos a
        JOIN usuarios u ON u.id = a.usuario_id
        ORDER BY a.logado_em DESC
        LIMIT ?
    """, (limite,)).fetchall()


def criar_usuario(conn: sqlite3.Connection, nome_usuario: str, senha: str, papel: str = "user") -> int:
    """Cadastra uma conta nova. Ao contrário de `estoque.adicionar_filamento`,
    nome duplicado aqui NÃO mescla — cada conta precisa de um usuário único
    pra logar, então vira erro claro em vez de comportamento implícito."""
    if not nome_usuario.strip():
        raise ValueError("Informe um nome de usuário.")
    if not senha:
        raise ValueError("Informe uma senha.")
    if papel not in ("admin", "user"):
        raise ValueError(f"papel inválido: {papel!r}")
    if conn.execute(
        "SELECT 1 FROM usuarios WHERE nome_usuario = ?", (nome_usuario.strip(),)
    ).fetchone():
        raise ValueError(f'Já existe uma conta com o usuário "{nome_usuario.strip()}".')

    hash_hex, salt_hex = _hash_senha(senha)
    agora = datetime.datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO usuarios (nome_usuario, senha_hash, senha_salt, papel, criado_em) "
        "VALUES (?, ?, ?, ?, ?)",
        (nome_usuario.strip(), hash_hex, salt_hex, papel, agora),
    )
    conn.commit()
    return cur.lastrowid


def alterar_usuario(
    conn: sqlite3.Connection,
    usuario_id: int,
    *,
    novo_nome: str | None = None,
    nova_senha: str | None = None,
    novo_papel: str | None = None,
):
    """Só troca o que for passado (None = mantém). Bloqueia remover
    `papel='admin'` do único admin restante — sem essa guarda, um clique
    errado no formulário trancaria todo mundo fora da aba Administração,
    sem forma de desfazer pela própria interface."""
    atual = buscar_usuario_por_id(conn, usuario_id)
    if atual is None:
        raise ValueError("Usuário não encontrado.")

    if novo_papel is not None and novo_papel not in ("admin", "user"):
        raise ValueError(f"papel inválido: {novo_papel!r}")
    if atual["papel"] == "admin" and novo_papel == "user":
        total_admins = conn.execute(
            "SELECT COUNT(*) AS n FROM usuarios WHERE papel = 'admin'"
        ).fetchone()["n"]
        if total_admins <= 1:
            raise ValueError("Não é possível remover o papel de administrador do único admin restante.")

    if novo_nome is not None:
        if not novo_nome.strip():
            raise ValueError("O nome de usuário não pode ficar em branco.")
        duplicado = conn.execute(
            "SELECT 1 FROM usuarios WHERE nome_usuario = ? AND id != ?",
            (novo_nome.strip(), usuario_id),
        ).fetchone()
        if duplicado:
            raise ValueError(f'Já existe uma conta com o usuário "{novo_nome.strip()}".')
        conn.execute("UPDATE usuarios SET nome_usuario = ? WHERE id = ?", (novo_nome.strip(), usuario_id))

    if nova_senha:
        hash_hex, salt_hex = _hash_senha(nova_senha)
        conn.execute(
            "UPDATE usuarios SET senha_hash = ?, senha_salt = ? WHERE id = ?",
            (hash_hex, salt_hex, usuario_id),
        )

    if novo_papel is not None:
        conn.execute("UPDATE usuarios SET papel = ? WHERE id = ?", (novo_papel, usuario_id))

    conn.commit()


def caminho_foto(usuario_row) -> Path | None:
    """Caminho completo da foto, ou None se a conta não tiver uma."""
    if not usuario_row["foto"]:
        return None
    return PASTA_FOTOS / usuario_row["foto"]


def definir_foto(conn: sqlite3.Connection, usuario_id: int, bytes_arquivo: bytes, extensao: str):
    """Salva a foto de perfil em `perfis/<id>.<extensão>` e atualiza a
    coluna `foto`. Nome pelo `id` (não pelo `nome_usuario`) — fica estável
    mesmo se a conta for renomeada depois, e não herda nenhum caractere
    problemático de nome de usuário digitado livremente."""
    extensao = extensao.lower().lstrip(".")
    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValueError(f"Formato de foto não suportado: {extensao}. Use jpg, jpeg ou png.")
    if len(bytes_arquivo) > TAMANHO_MAXIMO_FOTO:
        raise ValueError(f"Foto muito grande (máx. {TAMANHO_MAXIMO_FOTO // (1024 * 1024)}MB).")

    PASTA_FOTOS.mkdir(exist_ok=True)
    for antiga in PASTA_FOTOS.glob(f"{usuario_id}.*"):
        antiga.unlink()

    nome_arquivo = f"{usuario_id}.{extensao}"
    (PASTA_FOTOS / nome_arquivo).write_bytes(bytes_arquivo)
    conn.execute("UPDATE usuarios SET foto = ? WHERE id = ?", (nome_arquivo, usuario_id))
    conn.commit()


def seed_inicial(conn: sqlite3.Connection):
    """Cria as duas contas que já estavam em produção via
    `.streamlit/secrets.toml` (`[auth]`, removido nesta migração) — só
    roda se `usuarios` estiver vazia, pra preservar o login de quem já usa
    o sistema sem exigir recadastro manual no dia em que essa mudança
    entrou no ar (12/08/2026)."""
    if conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        return
    criar_usuario(conn, "admin", "2001", papel="admin")
    criar_usuario(conn, "pretomacaco", "penis", papel="user")
