
from contextlib import asynccontextmanager
from pathlib import Path
from functools import wraps
import logging
import sqlite3

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator


# =====================================================
# 1. CONFIGURAÇÕES GERAIS
# =====================================================

# Configura o registro de erros no terminal.
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Define o caminho do arquivo SQLite.
DB_PATH = Path(__file__).resolve().parent / "usuarios.db"


# =====================================================
# 2. CONEXÃO COM O BANCO DE DADOS
# =====================================================

def conectar():
    """
    Estabelece uma conexão com o banco SQLite.

    row_factory permite acessar colunas pelo nome.
    foreign_keys habilita a integridade referencial.
    """
    conexao = sqlite3.connect(DB_PATH, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


def criar_tabelas():
    """
    Cria as tabelas usuarios e enderecos caso
    ainda não existam no banco de dados.
    """

    with conectar() as conexao:

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                cpf TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                idade INTEGER NOT NULL
            )
        """)

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS enderecos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf_usuario TEXT NOT NULL,
                logradouro TEXT NOT NULL,
                numero TEXT NOT NULL,
                cidade TEXT NOT NULL,
                uf TEXT NOT NULL,
                cep TEXT NOT NULL,
                FOREIGN KEY (cpf_usuario)
                    REFERENCES usuarios(cpf)
            )
        """)


# =====================================================
# 3. TRATAMENTO CENTRALIZADO DE ERROS
# =====================================================

def tratar_erros_banco(func):
    """
    Decorator para tratar falhas de acesso ao SQLite.

    Preserva os erros HTTP definidos nos endpoints.

    HTTP 500: falha interna de acesso ao banco.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        try:
            return func(*args, **kwargs)

        except HTTPException:
            # Preserva erros como 404 e 409.
            raise

        except sqlite3.Error:
            # Registra o erro técnico no servidor.
            logger.exception(
                "Erro durante operação no banco SQLite"
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno de acesso ao banco de dados"
            )

    return wrapper


# =====================================================
# 4. INICIALIZAÇÃO DA APLICAÇÃO
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Inicializa as tabelas antes de disponibilizar
    a API para receber requisições.
    """

    criar_tabelas()
    yield


app = FastAPI(
    title="API REST de Usuários",
    description="API desenvolvida com FastAPI e SQLite",
    version="1.1.0",
    lifespan=lifespan
)


# =====================================================
# 5. MODELOS DE DADOS
# =====================================================

class Usuario(BaseModel):
    """
    Modelo para cadastro e consulta de usuários.
    """

    cpf: str = Field(min_length=11, max_length=11)
    nome: str = Field(min_length=2)
    email: str = Field(min_length=3)
    idade: int = Field(ge=0, le=120)

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, valor):
        # Verifica se o CPF contém 11 dígitos numéricos.
        # Não valida os dígitos verificadores.
        if not valor.isdigit():
            raise ValueError(
                "CPF deve conter 11 dígitos numéricos"
            )
        return valor


class Endereco(BaseModel):
    """
    Modelo para cadastro de endereços.
    """

    logradouro: str = Field(min_length=3)
    numero: str = Field(min_length=1)
    cidade: str = Field(min_length=2)
    uf: str = Field(min_length=2, max_length=2)
    cep: str = Field(min_length=8, max_length=8)


class EnderecoResposta(Endereco):
    """
    Modelo de resposta com ID e CPF do usuário.
    """

    id: int
    cpf_usuario: str


# =====================================================
# 6. POST - CADASTRAR USUÁRIO
# =====================================================

@app.post(
    "/usuarios",
    status_code=status.HTTP_201_CREATED,
    response_model=Usuario,
    responses={
        409: {"description": "CPF ou e-mail já cadastrado"},
        422: {"description": "Dados inválidos"},
        500: {"description": "Erro interno do banco de dados"}
    }
)
@tratar_erros_banco
def cadastrar_usuario(usuario: Usuario):
    """
    Insere um novo usuário na tabela usuarios.

    HTTP 201: usuário cadastrado.
    HTTP 409: CPF ou e-mail duplicado.
    HTTP 422: dados inválidos.
    HTTP 500: falha de acesso ao banco.
    """

    try:
        with conectar() as conexao:

            conexao.execute("""
                INSERT INTO usuarios
                    (cpf, nome, email, idade)
                VALUES (?, ?, ?, ?)
            """, (
                usuario.cpf,
                usuario.nome,
                usuario.email,
                usuario.idade
            ))

    except sqlite3.IntegrityError as erro:

        # Identifica violações de unicidade.
        if (
            erro.sqlite_errorname
            == "SQLITE_CONSTRAINT_UNIQUE"
            or erro.sqlite_errorname
            == "SQLITE_CONSTRAINT_PRIMARYKEY"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="CPF ou e-mail já cadastrado"
            )

        # Outros erros de integridade são tratados
        # como falhas internas pelo decorator.
        raise

    return usuario


# =====================================================
# 7. POST - CADASTRAR ENDEREÇO
# =====================================================

@app.post(
    "/usuarios/{cpf}/enderecos",
    status_code=status.HTTP_201_CREATED,
    response_model=EnderecoResposta,
    responses={
        404: {"description": "Usuário não encontrado"},
        422: {"description": "Dados inválidos"},
        500: {"description": "Erro interno do banco de dados"}
    }
)
@tratar_erros_banco
def cadastrar_endereco(cpf: str, endereco: Endereco):
    """
    Insere um endereço vinculado a um usuário.

    HTTP 201: endereço cadastrado.
    HTTP 404: usuário não encontrado.
    HTTP 422: dados inválidos.
    HTTP 500: falha de acesso ao banco.
    """

    with conectar() as conexao:

        # Verifica a existência do usuário.
        usuario = conexao.execute("""
            SELECT cpf
            FROM usuarios
            WHERE cpf = ?
        """, (cpf,)).fetchone()

        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        # Insere o endereço associado ao CPF.
        cursor = conexao.execute("""
            INSERT INTO enderecos
                (cpf_usuario, logradouro, numero,
                 cidade, uf, cep)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cpf,
            endereco.logradouro,
            endereco.numero,
            endereco.cidade,
            endereco.uf,
            endereco.cep
        ))

        id_endereco = cursor.lastrowid

    return {
        "id": id_endereco,
        "cpf_usuario": cpf,
        **endereco.model_dump()
    }


# =====================================================
# 8. GET - LISTAR TODOS OS USUÁRIOS
# =====================================================

@app.get(
    "/usuarios",
    status_code=status.HTTP_200_OK,
    response_model=list[Usuario],
    responses={
        500: {"description": "Erro interno do banco de dados"}
    }
)
@tratar_erros_banco
def listar_usuarios():
    """
    Retorna todos os usuários cadastrados.

    HTTP 200: consulta realizada.
    HTTP 500: falha de acesso ao banco.

    Se não houver usuários, retorna uma lista vazia.
    """

    with conectar() as conexao:

        registros = conexao.execute("""
            SELECT cpf, nome, email, idade
            FROM usuarios
            ORDER BY nome
        """).fetchall()

    return [dict(registro) for registro in registros]


# =====================================================
# 9. GET - CONSULTAR USUÁRIO POR CPF
# =====================================================

@app.get(
    "/usuarios/{cpf}",
    status_code=status.HTTP_200_OK,
    response_model=Usuario,
    responses={
        404: {"description": "Usuário não encontrado"},
        500: {"description": "Erro interno do banco de dados"}
    }
)
@tratar_erros_banco
def buscar_usuario(cpf: str):
    """
    Consulta um usuário pelo CPF informado.

    HTTP 200: usuário encontrado.
    HTTP 404: usuário não encontrado.
    HTTP 500: falha de acesso ao banco.
    """

    with conectar() as conexao:

        registro = conexao.execute("""
            SELECT cpf, nome, email, idade
            FROM usuarios
            WHERE cpf = ?
        """, (cpf,)).fetchone()

    if registro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    return dict(registro)


# =====================================================
# 10. GET - CONSULTAR ENDEREÇOS POR CPF
# =====================================================

@app.get(
    "/usuarios/{cpf}/enderecos",
    status_code=status.HTTP_200_OK,
    response_model=list[EnderecoResposta],
    responses={
        404: {"description": "Usuário não encontrado"},
        500: {"description": "Erro interno do banco de dados"}
    }
)
@tratar_erros_banco
def listar_enderecos(cpf: str):
    """
    Consulta os endereços vinculados ao CPF.

    HTTP 200: consulta realizada.
    HTTP 404: usuário não encontrado.
    HTTP 500: falha de acesso ao banco.

    Se o usuário não possuir endereços,
    retorna uma lista vazia.
    """

    with conectar() as conexao:

        # Confirma que o usuário existe.
        usuario = conexao.execute("""
            SELECT cpf
            FROM usuarios
            WHERE cpf = ?
        """, (cpf,)).fetchone()

        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        # Consulta os endereços cadastrados.
        registros = conexao.execute("""
            SELECT id, cpf_usuario, logradouro,
                   numero, cidade, uf, cep
            FROM enderecos
            WHERE cpf_usuario = ?
            ORDER BY id
        """, (cpf,)).fetchall()

    return [dict(registro) for registro in registros]
