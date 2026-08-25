# 📁 Mapeamento e Arquitetura de Arquivos — VanguardSec AI

Este documento descreve detalhadamente a responsabilidade de cada diretório e arquivo presente na estrutura da plataforma **VanguardSec AI v1.0**.

---

## 📂 Diretórios do Projeto

### `📁 agentes/`
Contém os módulos de Inteligência Artificial organizados segundo a arquitetura Multi-Tier:
* **`agente_auditor.py` (Tier 1):** Conecta à API do Ollama (`qwen2.5-coder:7b`) para realizar a triagem inicial dos logs brutos, identificando IoCs (endereços IP maliciosos e falhas de login).
* **`agente_compliance.py` (Tier 2):** Processa os dados de auditoria junto ao modelo (`qwen2.5:3b`) para avaliar conformidade regulatória contra normas ISO/IEC 27001 e artigos da LGPD.
* **`agente_remediacao.py` (Tier 3):** Atua como Engenheiro SOAR (`qwen2.5-coder:7b`), compilando playbooks de contenção executáveis em Bash (Linux) ou PowerShell (Windows).

### `📁 modulos/`
Reúne as bibliotecas de suporte e conectores do sistema:
* **`coletor_ssh.py`:** Gerencia conexões SSH puras (via `paramiko`) para extrair indicadores telemétricos de ativos Linux e injetar comandos de bloqueio de firewall (UFW).
* **`coletor_winrm.py`:** Realiza sondagem e leitura remota de dados de auditoria em servidores Windows Server.
* **`gerador_pdf.py`:** Utiliza templates HTML/CSS para compilar o relatório executivo de auditoria e exportar o documento em PDF de alta resolução.
* **`chatops_bot.py`:** Implementa a integração com a API do Telegram (`python-telegram-bot`), gerenciando mensagens de alertas e callbacks de botões *inline* para bloqueios de IP remotamente.
* **`notificador.py`:** Módulo para despacho de payloads e alertas para endpoints Webhook (Slack, Discord ou coletores SIEM).
* **`politicas.py`:** Gerencia e fornece as políticas de segurança ativas e trechos de normas regulatórias para context base da IA.

### `📁 docs/`
Diretório reservado para diagramas, especificações técnicas, guias de implantação e mapeamento de arquivos (`ESTRUTURA_PROJETO.md`).

### `📁 politicas/`
Armazena arquivos e documentos de referência normativa (PDFs, Markdown ou TXT contendo regras internas da empresa, diretrizes ISO e guias de compliance).

### `📁 relatorios/`
Diretório de saída onde o sistema grava automaticamente os relatórios executivos gerados em formato PDF após cada varredura.

### `📁 chroma_db/`
Banco de dados vetorial local (mantido para indexação de documentos de políticas caso ativada a busca semântica RAG).

### `📁 .vscode/`
Configurações do ambiente de desenvolvimento do VS Code (lançamento de depuradores, variáveis e configurações do Pylance/Linter).

### `📁 __pycache__/` e `📁 venv/`
* **`__pycache__/`:** Arquivos bytecode compilados pelo Python para otimizar o tempo de execução.
* **`venv/`:** Ambiente virtual isolado contendo as dependências e bibliotecas Python do projeto.

---

## 📄 Arquivos Raiz

* **`app.py`:** Interface principal do sistema desenvolvida em Streamlit. Constrói o dashboard executivo *Glassmorphic*, gerencia os estados de auditoria, aciona a esteira de agentes e renderiza os gráficos e botões de ação.
* **`historico_scans.json`:** Base de dados local em formato JSON. Armazena o registro cronológico de todas as varreduras realizadas, métricas coletadas, diagnósticos e caminhos dos relatórios salvos.
* **`main.py` / `run_bot.py`:** Scripts de inicialização rápida e execução do serviço de bot do Telegram em segundo plano fora da interface Web.
* **`requirements.txt`:** Lista de todas as dependências Python necessárias para execução do projeto (`streamlit`, `plotly`, `paramiko`, `python-telegram-bot`, `weasyprint`, etc.).
* **`README.md`:** Documentação oficial de apresentação, guia de instalação, instruções de inicialização, diagrama de topologia e registro de autoria do projeto.
* **`.tkb`:** Arquivo temporário de suporte do ambiente de desenvolvimento.

---
*VanguardSec AI v1.0 — Mapeamento Estrutural do Repositório*