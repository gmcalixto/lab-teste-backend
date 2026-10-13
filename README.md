# Laboratório de Testes Automatizados de Backend

![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-REST-009688) ![Pytest](https://img.shields.io/badge/Testes-Pytest-orange) ![SQLite](https://img.shields.io/badge/Banco-SQLite-07405E)

Projeto didático para demonstrar **testes automatizados de uma API REST**, com Python, FastAPI, SQLite, Pytest e GitHub Actions. O foco é validar respostas JSON, códigos HTTP e regras de persistência, além de executar verificações em integração contínua (CI).

**Repositório:** https://github.com/gmcalixto/lab-teste-backend

## Objetivos de aprendizagem

- Construir e consumir endpoints REST usando os métodos `GET` e `POST`.
- Verificar códigos HTTP e contratos JSON por meio de asserções.
- Testar casos positivos e negativos: validação, duplicidade e recurso inexistente.
- Simular falhas de acesso ao SQLite e conferir a resposta `500`.
- Isolar dados de teste e evitar efeitos sobre a base de desenvolvimento.
- Automatizar testes no GitHub Actions e gerar relatórios HTML.

## Tecnologias

| Tecnologia | Papel no projeto |
| --- | --- |
| Python | Linguagem de implementação |
| FastAPI e Pydantic | Endpoints REST e validação dos dados |
| SQLite | Persistência de usuários e endereços |
| Pytest | Organização e execução dos testes |
| HTTPX / TestClient | Requisições de teste locais ou HTTP reais |
| pytest-html e pytest-metadata | Relatórios e metadados da execução |
| GitHub Actions | Execução automatizada dos testes na CI |

## Organização do repositório

```text
lab-teste-backend/
├── .github/workflows/  # Workflows de integração contínua
├── tests/              # Testes automatizados
├── main.py             # API FastAPI
├── popular_banco.py    # Carga de dados fictícios
├── usuarios.db         # Banco SQLite de exemplo
├── pytest.ini          # Configurações do Pytest
├── requirements.txt    # Dependências Python
└── README.md
```

> A estrutura acima representa os itens observados no repositório. Os nomes e cenários específicos dos testes e dos workflows devem ser conferidos nos arquivos da versão utilizada.

## Modelo de dados

A API mantém duas tabelas relacionadas:

- **`usuarios`**: `cpf` (chave primária), `nome`, `email` (único) e `idade`.
- **`enderecos`**: `id` (chave primária), `cpf_usuario` (chave estrangeira), `logradouro`, `numero`, `cidade`, `uf` e `cep`.

A relação é **1:N**: um usuário pode possuir vários endereços.

## Endpoints REST

| Método | Rota | Operação | Sucesso | Outros retornos previstos |
| --- | --- | --- | --- | --- |
| `POST` | `/usuarios` | Cadastrar usuário | `201` | `409`, `422`, `500` |
| `POST` | `/usuarios/{cpf}/enderecos` | Cadastrar endereço | `201` | `404`, `422`, `500` |
| `GET` | `/usuarios` | Listar usuários | `200` | `500` |
| `GET` | `/usuarios/{cpf}` | Buscar usuário pelo CPF | `200` | `404`, `500` |
| `GET` | `/usuarios/{cpf}/enderecos` | Listar endereços do usuário | `200` | `404`, `500` |

### Significado dos códigos HTTP

- **200 OK:** consulta realizada.
- **201 Created:** recurso cadastrado.
- **404 Not Found:** usuário solicitado não encontrado.
- **409 Conflict:** conflito de unicidade de CPF ou e-mail.
- **422 Unprocessable Entity:** dados de entrada não atendem às validações.
- **500 Internal Server Error:** erro de acesso ao SQLite tratado pela aplicação.

## Instalação e execução local

Recomenda-se Python 3.12 e Git.

```bash
git clone https://github.com/gmcalixto/lab-teste-backend.git
cd lab-teste-backend
python -m venv .venv
```

Ative o ambiente virtual:

```powershell
# Windows / PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Inicie a API:

```bash
fastapi dev main.py
```

Acesse **http://127.0.0.1:8000/docs** para utilizar a documentação Swagger e experimentar os endpoints. O SQLite é inicializado pela aplicação.

Para gerar dados de exemplo, em outro terminal na pasta do projeto:

```bash
python popular_banco.py
```

O script foi concebido para cadastrar até 100 usuários fictícios e endereços associados, evitando reinserir os mesmos registros em execuções posteriores. Use apenas dados sintéticos.

## Foco do laboratório: testes automatizados

O Pytest identifica funções com nomes iniciados por `test_` e verifica expectativas por meio de `assert`. Uma falha na asserção reprova o teste e faz a execução retornar um status de erro.

### Testes locais com TestClient

A abordagem local utiliza o `TestClient` do FastAPI, dispensando um servidor HTTP externo. Para evitar interferência entre testes, recomenda-se uma fixture com banco temporário (`tmp_path`) e substituição do caminho do SQLite (`monkeypatch`).

Exemplo ilustrativo de teste de consulta a um usuário inexistente:

```python
def test_usuario_inexistente(client):
    resposta = client.get('/usuarios/00000000000')
    assert resposta.status_code == 404
    assert resposta.json()['detail'] == 'Usuário não encontrado'
```

Outros cenários importantes incluem:

| Categoria | Verificação | HTTP esperado |
| --- | --- | --- |
| Cadastro | Usuário válido | `201` |
| Cadastro | CPF ou e-mail duplicado | `409` |
| Validação | CPF com tamanho incorreto | `422` |
| Consulta | Lista de usuários | `200` |
| Consulta | CPF não cadastrado | `404` |
| Endereço | Cadastro associado a usuário existente | `201` |
| Endereço | Cadastro associado a CPF inexistente | `404` |
| Persistência | Endereço retornado na consulta | `200` |
| Falha simulada | Exceção `sqlite3.OperationalError` | `500` |

> Os cenários listados constituem a matriz de verificação recomendada. A quantidade de testes aprovados deve ser obtida de uma execução real, não presumida.

### Executar os testes

```bash
# Todos os testes encontrados em tests/
python -m pytest

# Execução detalhada
python -m pytest -v --tb=short

# Apenas os testes locais (quando esse arquivo existir)
python -m pytest tests/test_main.py -v
```

O arquivo `pytest.ini` configura a descoberta dos testes e a saída detalhada (`addopts = -v`).

### Gerar relatório HTML

```bash
python -m pytest tests/test_main.py -v \
  --html=relatorio_testes.html \
  --self-contained-html
```

No PowerShell, utilize uma linha única:

```powershell
python -m pytest tests/test_main.py -v --html=relatorio_testes.html --self-contained-html
```

O relatório apresenta os testes executados, aprovações, falhas e informações do ambiente. Os parâmetros `--html` e `--self-contained-html` dependem da instalação de **pytest-html**.

### Testes contra um servidor externo

Quando houver testes HTTP externos, configure a URL do servidor:

```powershell
$env:API_BASE_URL = 'https://sua-api.exemplo.com'
python -m pytest tests/test_api_externa.py -v
```

Esses testes utilizam requisições reais e podem persistir dados no banco remoto. Execute-os **somente em ambiente de homologação autorizado**. Diferentemente dos testes locais, o `monkeypatch` não altera o banco ou os processos do servidor remoto.

## Integração contínua com GitHub Actions

O diretório `.github/workflows/` reúne os workflows do repositório. A ideia da CI é executar os testes automaticamente após alterações no código, com as seguintes etapas:

1. Obter o código com `actions/checkout`.
2. Preparar a versão de Python com `actions/setup-python`.
3. Instalar dependências com `pip install -r requirements.txt`.
4. Executar `python -m pytest` e gerar o relatório HTML.
5. Publicar o relatório como artefato usando `actions/upload-artifact`.

Para visualizar uma execução, abra a aba **[Actions](https://github.com/gmcalixto/lab-teste-backend/actions)**, selecione o workflow e consulte os logs de cada etapa. Se houver upload do relatório, ele ficará disponível nos artefatos da execução.

Uma estratégia recomendada é executar os testes locais em `push` e `pull_request`, mantendo testes externos com escrita em banco restritos a execução manual ou a um ambiente de homologação controlado.

## Critérios de qualidade demonstrados

- **Correção funcional:** o endpoint retorna os dados esperados.
- **Contrato HTTP:** cada cenário produz o código de resposta adequado.
- **Validação de entrada:** requisições inválidas são rejeitadas.
- **Integridade de dados:** CPF e e-mail únicos; endereços associados a usuários existentes.
- **Tratamento de falhas:** erros do SQLite são registrados e convertidos em resposta `500`.
- **Reprodutibilidade:** testes isolados não dependem da ordem de execução.
- **Automação:** a CI detecta regressões e oferece histórico de execuções.

## Limitações e boas práticas

Este é um projeto de laboratório. A API não deve ser exposta com CPFs reais ou dados pessoais sem autenticação, autorização, controles de acesso e outras medidas de proteção. O campo CPF valida o formato numérico, mas não os dígitos verificadores. O banco SQLite incluído no repositório deve conter somente dados fictícios.

Para evolução do projeto, considere adicionar testes parametrizados, cobertura de código com `pytest-cov`, isolamento explícito dos testes externos e uma regra de proteção da branch `main` que exija aprovação da CI.

## Referências

- [FastAPI — Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest — Documentação](https://docs.pytest.org/)
- [HTTPX — Documentação](https://www.python-httpx.org/)
- [pytest-html](https://pytest-html.readthedocs.io/)
- [GitHub Actions — Documentação](https://docs.github.com/en/actions)

---

**Finalidade:** demonstração prática de desenvolvimento de APIs REST, testes automatizados e integração contínua em aplicações backend Python.
