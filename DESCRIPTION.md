# Descrição Detalhada do Projeto: Motor de Regras Modbus

## Visão Geral

Este projeto expande um simulador e controlador Modbus RTU existente, adicionando um "Motor de Regras" dinâmico. O objetivo é permitir que o sistema tome decisões autônomas com base em condições pré-definidas, sem a necessidade de alterar o código-fonte do controlador principal.

O motor de regras permite a criação de lógicas de controle personalizadas, como "se o nível do reservatório X for inferior a 20%, então ligue a bomba Y". Isso torna o sistema mais flexível e adaptável a diferentes cenários operacionais.

## Arquitetura

A arquitetura do projeto é dividida em três componentes principais:

1.  **Simulador de Escravos Modbus (`modbus_slaves.py`):**
    *   Simula dispositivos Modbus RTU (reservatórios, motobomba) em um ambiente virtual.
    *   Os valores dos registradores (níveis, tensões, etc.) são atualizados dinamicamente para simular um ambiente real.
    *   Opera em uma porta serial virtual criada com `socat`.

2.  **Controlador Modbus (`app/modbus_master.py`):**
    *   Atua como o mestre Modbus RTU, lendo e escrevendo nos registradores dos escravos simulados.
    *   Interage com o banco de dados para buscar configurações e registrar dados operacionais.
    *   **Com a nova funcionalidade**, o controlador também irá:
        *   Carregar as regras do banco de dados.
        *   Avaliar as condições das regras em cada ciclo de leitura.
        *   Executar as ações correspondentes se as condições forem atendidas.

3.  **Interface de Gerenciamento (Flask):**
    *   Uma aplicação web para visualizar dados, configurar dispositivos e, com a nova funcionalidade, gerenciar as regras, condições e ações do motor de regras.

## Árvore de Arquivos

```
.
├── app/
│   ├── models/
│   │   ├── __init__.py             # Inicializa o módulo de modelos
│   │   ├── regra_model.py          # Novo: Modelo para a tabela de Regras
│   │   ├── condicao_model.py       # Novo: Modelo para a tabela de Condições
│   │   ├── acao_model.py           # Novo: Modelo para a tabela de Ações
│   │   ├── modbus_model.py         # Modelo para dispositivos e registradores Modbus
│   │   ├── reservatorio_model.py   # Modelo para os reservatórios
│   │   └── motobomba_model.py      # Modelo para as motobombas
│   ├── services/                   # Lógica de negócios e serviços
│   │   └── ...
│   ├── static/                     # Arquivos estáticos (CSS, JS, imagens)
│   │   └── ...
│   ├── templates/                  # Templates HTML (Jinja2)
│   │   └── ...
│   ├── views/                      # Rotas e views da aplicação Flask
│   │   └── ...
│   ├── __init__.py                 # Inicializa a aplicação Flask
│   ├── modbus_master.py            # Lógica do mestre Modbus
│   └── ...
├── data/
│   └── app.db                      # Banco de dados SQLite
├── migrations/                     # Scripts de migração do banco de dados (Alembic)
│   └── ...
├── README.md                       # Documentação principal do projeto
├── DESCRIPTION.md                  # Descrição detalhada do projeto e novas funcionalidades
├── config.py                       # Configurações da aplicação
├── modbus_slaves.py                # Simulador de escravos Modbus
├── requirements.txt                # Dependências Python do projeto
└── ...
```
