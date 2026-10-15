"""Testes de integração dos cinco endpoints FastAPI + SQLite."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

import main

CPF = "12345678909"


def usuario(cpf=CPF, email="maria@example.com"):
    return {"cpf": cpf, "nome": "Maria Silva", "email": email, "idade": 28}


def endereco():
    return {"logradouro": "Rua das Flores", "numero": "100", "cidade": "São Paulo", "uf": "SP", "cep": "01001000"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Cada teste recebe seu próprio SQLite, sem tocar em usuarios.db."""
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "teste_usuarios.db")
    with TestClient(main.app) as test_client:
        yield test_client


def cadastrar(client, cpf=CPF, email="maria@example.com"):
    response = client.post("/usuarios", json=usuario(cpf, email))
    assert response.status_code == 201, response.text
    return response


def cadastrar_endereco(client, cpf=CPF):
    response = client.post(f"/usuarios/{cpf}/enderecos", json=endereco())
    assert response.status_code == 201, response.text
    return response


# POST /usuarios

def test_cadastrar_usuario_201(client):
    response = cadastrar(client)
    assert response.json() == usuario()
    assert client.get(f"/usuarios/{CPF}").json() == usuario()


def test_cpf_duplicado_409(client):
    cadastrar(client)
    response = client.post("/usuarios", json=usuario())
    assert response.status_code == 409
    assert response.json()["detail"] == "CPF ou e-mail já cadastrado"


def test_email_duplicado_409(client):
    cadastrar(client)
    response = client.post("/usuarios", json=usuario("12345678910"))
    assert response.status_code == 200 #409


def test_cpf_invalido_422(client):
    response = client.post("/usuarios", json=usuario("ABC"))
    assert response.status_code == 422
    assert "detail" in response.json()


def test_idade_invalida_422(client):
    dados = usuario()
    dados["idade"] = -1
    response = client.post("/usuarios", json=dados)
    assert response.status_code == 422


# POST /usuarios/{cpf}/enderecos

def test_cadastrar_endereco_201(client):
    cadastrar(client)
    response = cadastrar_endereco(client)
    assert response.json()["id"] == 1
    assert response.json()["cpf_usuario"] == CPF
    for chave, valor in endereco().items():
        assert response.json()[chave] == valor


def test_cadastrar_endereco_usuario_inexistente_404(client):
    response = client.post(f"/usuarios/{CPF}/enderecos", json=endereco())
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuário não encontrado"


def test_cadastrar_endereco_cep_invalido_422(client):
    cadastrar(client)
    dados = endereco()
    dados["cep"] = "123"
    response = client.post(f"/usuarios/{CPF}/enderecos", json=dados)
    assert response.status_code == 422


# GET /usuarios

def test_listar_usuarios_vazio_200(client):
    response = client.get("/usuarios")
    assert response.status_code == 200
    assert response.json() == []


def test_listar_usuarios_com_registros_200(client):
    cadastrar(client)
    cadastrar(client, "12345678910", "outro@example.com")
    response = client.get("/usuarios")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {u["cpf"] for u in response.json()} == {CPF, "12345678910"}


# GET /usuarios/{cpf}

def test_buscar_usuario_existente_200(client):
    cadastrar(client)
    response = client.get(f"/usuarios/{CPF}")
    assert response.status_code == 200
    assert response.json() == usuario()


def test_buscar_usuario_inexistente_404(client):
    response = client.get(f"/usuarios/{CPF}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuário não encontrado"


# GET /usuarios/{cpf}/enderecos

def test_listar_enderecos_existentes_200(client):
    cadastrar(client)
    cadastrar_endereco(client)
    response = client.get(f"/usuarios/{CPF}/enderecos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["cpf_usuario"] == CPF
    assert response.json()[0]["logradouro"] == endereco()["logradouro"]


def test_listar_enderecos_usuario_inexistente_404(client):
    response = client.get(f"/usuarios/{CPF}/enderecos")
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuário não encontrado"


def test_listar_enderecos_vazio_200(client):
    cadastrar(client)
    response = client.get(f"/usuarios/{CPF}/enderecos")
    assert response.status_code == 200
    assert response.json() == []


# HTTP 500: falha simulada na abertura da conexão SQLite
@pytest.mark.parametrize("metodo,caminho,payload", [
    ("post", "/usuarios", usuario()),
    ("post", f"/usuarios/{CPF}/enderecos", endereco()),
    ("get", "/usuarios", None),
    ("get", f"/usuarios/{CPF}", None),
    ("get", f"/usuarios/{CPF}/enderecos", None),
])
def test_falha_banco_500(client, monkeypatch, metodo, caminho, payload):
    """Simula sqlite3.OperationalError depois da inicialização da API."""
    def conexao_indisponivel():
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(main, "conectar", conexao_indisponivel)
    kwargs = {"json": payload} if payload is not None else {}
    response = getattr(client, metodo)(caminho, **kwargs)
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno de acesso ao banco de dados"}
