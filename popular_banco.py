
import sqlite3
import random
from pathlib import Path

# =====================================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS
# =====================================================

# Utiliza o mesmo banco de dados do main.py.
DB_PATH = Path(__file__).resolve().parent / "usuarios.db"

# Permite reproduzir os mesmos dados em cada execução.
random.seed(42)

# Quantidade de usuários que serão gerados.
TOTAL_USUARIOS = 100


# =====================================================
# 2. DADOS FICTÍCIOS PARA GERAÇÃO
# =====================================================

nomes = [
    "Ana", "Bruno", "Carlos", "Daniela", "Eduardo",
    "Fernanda", "Gabriel", "Helena", "Igor", "Juliana",
    "Lucas", "Mariana", "Nicolas", "Patricia", "Rafael",
    "Renata", "Ricardo", "Sofia", "Thiago", "Vanessa"
]

sobrenomes = [
    "Silva", "Santos", "Oliveira", "Souza", "Pereira",
    "Costa", "Rodrigues", "Almeida", "Nascimento",
    "Lima", "Araujo", "Ferreira", "Carvalho"
]

logradouros = [
    "Rua das Flores",
    "Avenida Brasil",
    "Rua dos Pinheiros",
    "Avenida Paulista",
    "Rua da Liberdade",
    "Rua das Acacias",
    "Avenida Central",
    "Rua Sao Jose",
    "Rua das Palmeiras",
    "Avenida Independencia"
]

# Cidade, UF e prefixo de CEP fictício.
localidades = [
    ("São Paulo", "SP", "01001"),
    ("Campinas", "SP", "13010"),
    ("Rio de Janeiro", "RJ", "20010"),
    ("Belo Horizonte", "MG", "30110"),
    ("Curitiba", "PR", "80010"),
    ("Porto Alegre", "RS", "90010"),
    ("Salvador", "BA", "40010"),
    ("Recife", "PE", "50010"),
    ("Fortaleza", "CE", "60010"),
    ("Brasília", "DF", "70040")
]


# =====================================================
# 3. GERAÇÃO DE CPF FICTÍCIO
# =====================================================

def gerar_cpf_ficticio(numero):
    """
    Gera um identificador numérico de 11 dígitos.

    Os CPFs gerados são identificadores sintéticos,
    não destinados à identificação de pessoas reais.

    A sequência utiliza o número do registro para
    garantir identificadores distintos.
    """

    return f"999{numero:08d}"


# =====================================================
# 4. CONEXÃO COM O SQLITE
# =====================================================

def conectar():
    """
    Estabelece conexão com o banco SQLite
    utilizado pela aplicação FastAPI.
    """

    conexao = sqlite3.connect(DB_PATH)
    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


# =====================================================
# 5. CRIAÇÃO DAS TABELAS
# =====================================================

def criar_tabelas(conexao):
    """
    Cria as tabelas caso ainda não existam.

    Mantém a mesma estrutura utilizada
    pelo arquivo main.py.
    """

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
# 6. POPULAR A BASE DE DADOS
# =====================================================

def popular_banco():
    """
    Insere 100 usuários e seus respectivos endereços.

    Evita duplicidade de usuários e endereços
    durante execuções posteriores.
    """

    usuarios_inseridos = 0
    enderecos_inseridos = 0

    try:
        with conectar() as conexao:

            criar_tabelas(conexao)

            for i in range(1, TOTAL_USUARIOS + 1):

                # -------------------------------------
                # GERAÇÃO DOS DADOS DO USUÁRIO
                # -------------------------------------

                cpf = gerar_cpf_ficticio(i)

                nome = (
                    f"{random.choice(nomes)} "
                    f"{random.choice(sobrenomes)}"
                )

                email = f"usuario{i:03d}@example.com"

                idade = random.randint(18, 75)

                # Verifica se o usuário já existe.
                usuario_existe = conexao.execute("""
                    SELECT cpf
                    FROM usuarios
                    WHERE cpf = ?
                """, (cpf,)).fetchone()

                if usuario_existe is None:

                    conexao.execute("""
                        INSERT INTO usuarios
                            (cpf, nome, email, idade)
                        VALUES (?, ?, ?, ?)
                    """, (
                        cpf,
                        nome,
                        email,
                        idade
                    ))

                    usuarios_inseridos += 1

                # -------------------------------------
                # GERAÇÃO DOS DADOS DO ENDEREÇO
                # -------------------------------------

                logradouro = random.choice(logradouros)
                numero = str(random.randint(1, 2000))

                cidade, uf, prefixo_cep = random.choice(
                    localidades
                )

                cep = f"{prefixo_cep}{i:03d}"

                # Verifica se o usuário já possui endereço.
                endereco_existe = conexao.execute("""
                    SELECT id
                    FROM enderecos
                    WHERE cpf_usuario = ?
                """, (cpf,)).fetchone()

                if endereco_existe is None:

                    conexao.execute("""
                        INSERT INTO enderecos
                            (cpf_usuario, logradouro,
                             numero, cidade, uf, cep)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        cpf,
                        logradouro,
                        numero,
                        cidade,
                        uf,
                        cep
                    ))

                    enderecos_inseridos += 1

            # Confirma todas as inserções.
            conexao.commit()

            # -------------------------------------
            # CONSULTA DE TOTAIS
            # -------------------------------------

            total_usuarios = conexao.execute("""
                SELECT COUNT(*) FROM usuarios
            """).fetchone()[0]

            total_enderecos = conexao.execute("""
                SELECT COUNT(*) FROM enderecos
            """).fetchone()[0]

        print("\n====================================")
        print("   POPULAÇÃO DO BANCO CONCLUÍDA")
        print("====================================")
        print(f"Usuários inseridos: {usuarios_inseridos}")
        print(f"Endereços inseridos: {enderecos_inseridos}")
        print("------------------------------------")
        print(f"Total de usuários: {total_usuarios}")
        print(f"Total de endereços: {total_enderecos}")
        print("====================================\n")

    except sqlite3.Error as erro:

        print("\nErro ao acessar o banco SQLite:")
        print(erro)


# =====================================================
# 7. EXECUÇÃO DO SCRIPT
# =====================================================

if __name__ == "__main__":
    popular_banco()
