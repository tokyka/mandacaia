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