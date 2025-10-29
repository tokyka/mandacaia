# Mandacaia - Controlador e Simulador Modbus RTU

Este projeto implementa um sistema de controle e um ambiente de simulação para comunicação Modbus RTU. A arquitetura é composta por um mestre controlador que interage com um banco de dados e um servidor que simula múltiplos escravos com dados dinâmicos.

O projeto é dividido em duas partes principais:

1.  **O Controlador (`app/modbus_master.py`):** Atua como o cérebro do sistema. É um mestre Modbus RTU que lê configurações de um banco de dados, monitora os níveis de reservatórios, controla uma motobomba e armazena todos os dados de operação.
2.  **O Simulador de Escravos (`modbus_slaves.py`):** Atua como o "hardware" virtual. É um servidor Modbus RTU que simula três dispositivos escravos: uma motobomba e dois reservatórios, cujos valores (tensão, corrente, níveis) mudam dinamicamente.

---

## Arquitetura e Execução

Para executar o sistema, você precisará de três terminais: um para a ponte de comunicação serial, um para os escravos (servidor) e um para o controlador (mestre).

**Pré-requisitos:**
*   Dependências do Python instaladas: `pip install -r requirements.txt`
*   Utilitário `socat` instalado: `sudo apt-get install socat`
*   Banco de dados configurado e tabelas criadas: `flask db upgrade`
*   Dados iniciais no banco (reservatórios, alertas, etc.).

### Passo 1: Criar a Ponte Serial Virtual

O `socat` cria um par de portas seriais virtuais (`/tmp/ttyS0` e `/tmp/ttyS1`) para que o mestre e os escravos possam se comunicar. Execute em um terminal e deixe-o rodando:

```bash
socat -d -d PTY,raw,echo=0,link=/tmp/ttyS0 PTY,raw,echo=0,link=/tmp/ttyS1
```

### Passo 2: Iniciar o Simulador de Escravos (Servidor)

Em um **segundo terminal**, execute o script dos escravos. Ele irá escutar por conexões na porta `/tmp/ttyS0`.

```bash
python modbus_slaves.py
```
*   **Saída esperada:** Você verá logs da "Thread de atualização de valores" mostrando os dados da bomba e dos reservatórios sendo alterados em tempo real.

### Passo 3: Iniciar o Controlador (Mestre)

Em um **terceiro terminal**, execute o script do controlador principal. Ele se conectará aos escravos via `/tmp/ttyS1` e iniciará a lógica de controle.

```bash
python -m app.modbus_master
```
*   **Saída esperada:** Você verá logs do controlador, como "Nível Lido...", "Condição de acionamento atingida...", etc., indicando que ele está operando e interagindo com os escravos e o banco de dados.

---

## Teste de Comunicação Simples

Para verificar a comunicação RTU de forma isolada (sem o banco de dados), você pode usar o cliente de teste `modbus_master.py`.

1.  Execute os Passos 1 e 2 acima.
2.  No terceiro terminal, em vez do controlador principal, execute:
    ```bash
    python modbus_master.py
    ```
*   **Saída esperada:** Ciclos de leitura e escrita, mostrando os valores lidos de cada um dos 3 escravos.

---

## Debugging Alembic `ValueError` (Data too long for column / Enum issues)

If you encounter `ValueError: not enough values to unpack` or `Data too long for column` errors during `flask db migrate`, especially related to `ENUM` types, it might be due to how Alembic's autogenerate feature interacts with MariaDB's `ENUM` representation.

Here's a debugging step that can help pinpoint the exact problematic column:

1.  **Add detailed logging to Alembic's `impl.py`:**
    *   Locate the file: `YOUR_VENV_PATH/lib/pythonX.Y/site-packages/alembic/ddl/impl.py` (replace `YOUR_VENV_PATH` and `pythonX.Y` with your actual virtual environment path and Python version).
    *   Open the file and find the `_tokenize_column_type` function (around line 530-540).
    *   Modify the `for` loop within this function to include a logger call, like this:

        ```python
                if paren_term:
                    term: str
                    _logger = logging.getLogger(__name__) # Add this line
                    for term in re.findall("[^(),]+", paren_term):
                        _logger.info(f"DEBUG _tokenize_column_type: paren_term='{paren_term}', term='{term}'") # Add this line
                        if "=" in term:
                            key, val = term.split("=")
                            params.kwargs[key.strip()] = val.strip()
                        else:
                            params.args.append(term.strip())
        ```
    *   Also, ensure `import logging` is at the top of `alembic/ddl/impl.py`.

2.  **Run `flask db migrate`:**
    *   Execute `flask db migrate -m "Debug migration"`
    *   The console output will now show `DEBUG _tokenize_column_type` messages, indicating the `paren_term` and `term` values that Alembic is trying to process. This should help identify the specific column causing the `ValueError`.

3.  **Revert changes:** After debugging, remember to revert these changes in `alembic/ddl/impl.py` to avoid polluting your logs.

---