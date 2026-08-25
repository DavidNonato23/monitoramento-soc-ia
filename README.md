
```markdown
# 🛡️ VanguardSec AI — Global Command SOC & SOAR (v1.0)

> **Next-Gen Autonomous Cyber Defense Platform**  
> Plataforma autônoma de SecOps, Threat Intelligence e Resposta a Incidentes alimentada por Inteligência Artificial local via Ollama.

---

## 👨‍💻 Autor e Desenvolvedor

* **Idealização, Arquitetura & Engenharia:** [David Nonato](https://github.com/DavidNonato23)
* **GitHub:** [@DavidNonato23](https://github.com/DavidNonato23)
* **Projeto:** [VanguardSec AI — Global Command SOC & SOAR v1.0](https://github.com/DavidNonato23/vanguardsec-ai)

---

## 🗺️ Topologia e Arquitetura do Sistema

A topologia do **VanguardSec AI** adota um modelo *agentless* (sem agentes instalados nos servidores monitorados). 

A comunicação ocorre de forma centralizada entre:
* **Engine de IA Local:** Processamento inteligente das ameaças via Ollama.
* **Coletores de Telemetria Remota:** Extração de dados de infraestrutura.
* **Interface Executiva:** Painéis visuais para monitoramento.
* **Canais de Resposta Automática (SOAR / ChatOps):** Mitigação de incidentes e interação via Telegram.

```text
               +-------------------------------------------------+
               |             INFRAESTRUTURA ALVO                 |
               |                                                 |
               |   [ Servidor Linux / Windows ]                  |
               |   • Auth Logs / Open Ports / TCP Connections    |
               |   • UFW Firewall / Windows Firewall             |
               +-----------------------+-------------------------+
                                       ^
                                       | (Coleta Agentless via SSH/WinRM
                                       |  e Injeção de Fixes SOAR)
                                       v
               +-----------------------+-------------------------+
               |             VANGUARDSEC AI ENGINE               |
               |                                                 |
               |   +-------------------------------------------+ |
               |   |            Coletores Telemétricos         | |
               |   |          (Paramiko / WinRM Modules)       | |
               |   +---------------------+---------------------+ |
               |                         |                       |
               |                         v                       |
               |   +-------------------------------------------+ |
               |   |    Pipeline Multi-Tier IA (Ollama Local)  | |
               |   |                                           | |
               |   | • Tier 1: Analista (qwen2.5-coder:7b)     | |
               |   | • Tier 2: Compliance (qwen2.5:3b)         | |
               |   | • Tier 3: Engenheiro SOAR (qwen2.5-coder) | |
               |   +---------------------+---------------------+ |
               +-----------------------+-------------------------+
                                       |
                    +------------------+------------------+
                    |                                     |
                    v                                     v
+-------------------------------------+   +-------------------------------------+
|      DASHBOARD EXECUTIVE (Streamlit)|   |CHATOPS & NOTIFICADORES (External)   |
|                                     |   |                                     |
| • Card de Status Visual (Red/Green) |   | • Telegram Bot (Ações Inline)       |
| • Diagnóstico Simplificado LGPD     |   | • Webhooks (Slack / Discord / SIEM) |
| • Botão de Bloqueio Instantâneo     |   | • Relatórios Executivos PDF         |
+-------------------------------------+   +-------------------------------------+

```

### 🔄 Fluxo de Comunicação e Dados

1. **Sondagem Telemétrica (Inbound):** O módulo coletor realiza conexões remotas seguras (SSH/WinRM) para obter dados de conexões ativas (`TCP ESTABLISHED`), serviços escutando portas (`LISTEN`) e logs de tentativas de autenticação (`auth.log`).
2. **Processamento Multi-Tier (Local LLM):** A telemetria passa pelo pipeline de IA no Ollama local:
* **Tier 1 (Analista):** Extrai IoCs (IPs atacantes, porta-alvo e contagem de investidas).
* **Tier 2 (Compliance):** Classifica a severidade do risco sob as normas LGPD e ISO 27001.
* **Tier 3 (Engenheiro SOAR):** Compila o Playbook de contenção executável (`sudo ufw deny`).


3. **Apresentação e Disparo de Alertas (Outbound):** Os resultados alimentam a interface *Glassmorphism* do Streamlit, geram o relatório em PDF e despacham alertas interativos para o aplicativo do Telegram.
4. **Remediação Bidirecional (SOAR Action):** Ao acionar o bloqueio (seja pelo botão do Dashboard ou do Telegram), o comando de firewall é injetado diretamente na infraestrutura alvo para isolar a ameaça em tempo real.

---

## 📌 Visão Geral do Projeto

O **VanguardSec AI** é uma solução completa de segurança cibernética criada para fechar a lacuna entre a complexidade técnica dos logs de segurança e a tomada de decisão executiva.

---

## 🎨 Principais Destaques

* **Dashboard Executivo Glassmorphism:** Interface visual intuitiva, limpa e mastigada para diretores e clientes não técnicos, acompanhada de aba dedicada para engenharia de TI.
* **Esteira Multi-Tier de IA (Ollama):**
* **Tier 1 — Analista SOC (`qwen2.5-coder:7b`):** Triagem inicial e extração de Indicadores de Comprometimento (IoCs).
* **Tier 2 — Especialista em Riscos (`qwen2.5:3b`):** Avaliação de impacto regulatório e conformidade com LGPD/ISO 27001.
* **Tier 3 — Engenheiro SOAR (`qwen2.5-coder:7b`):** Construção de Playbooks executáveis de contenção (UFW / PowerShell).


* **Automação ChatOps Bidirecional:** Alertas instantâneos no Telegram com botões *inline* que permitem bloquear IPs invasores com apenas 1 clique no celular.
* **Relatórios & Logs SIEM:** Geração automática de relatórios executivos em PDF e exportação de logs de auditoria no padrão CEF (Common Event Format).

---

## 📂 Estrutura do Repositório

```text
VanguardSec-AI/
├── agentes/
│   ├── agente_auditor.py         # Tier 1: Analista de SOC (Triagem & IoCs)
│   ├── agente_compliance.py      # Tier 2: Especialista em Riscos e Compliance
│   └── agente_remediacao.py      # Tier 3: Engenheiro SOAR (Playbooks de Contenção)
├── modulos/
│   ├── coletor_ssh.py            # Coleta de telemetria remota Linux via Paramiko
│   ├── coletor_winrm.py          # Coleta de telemetria remota Windows
│   ├── gerador_pdf.py            # Geração de relatórios executivos em PDF
│   ├── chatops_bot.py            # Bot do Telegram e callbacks de bloqueio
│   ├── notificador.py            # Webhooks (Slack / Discord / SIEM)
│   └── politicas.py              # Módulo de políticas ativas e normas
├── relatorios/                   # Diretório de relatórios PDF gerados
├── app.py                        # Aplicação principal Streamlit
├── historico_scans.json          # Base de dados local em formato JSON
├── requirements.txt              # Dependências Python
└── README.md                     # Documentação do projeto

```

---

## 🛠️ Pré-requisitos

* **Python:** Versão 3.10 ou superior.
* **Ollama Engine:** Instalado e em execução na porta local padrão (`http://localhost:11434`).
* **Modelos LLM:**
* `qwen2.5-coder:7b`
* `qwen2.5:3b`


* **Acesso Remoto:** SSH ativado no servidor alvo (Linux) ou WinRM habilitado (Windows).

---

## 🚀 Guia de Instalação e Execução

### 1. Clonar o Repositório e Configurar o Ambiente

```bash
git clone [https://github.com/DavidNonato23/vanguardsec-ai.git](https://github.com/DavidNonato23/vanguardsec-ai.git)
cd vanguardsec-ai

# Criar e ativar o ambiente virtual
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

```

### 2. Baixar os Modelos no Ollama

Abra o terminal e execute o download das IAs utilizadas pelos agentes:

```bash
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5:3b

```

### 3. Iniciar o Dashboard

```bash
streamlit run app.py

```

Acesse o painel executivo pelo navegador através do endereço: `http://localhost:8501`

---

## 📱 Configuração do ChatOps Telegram (Opcional)

Para receber alertas de incidentes e acionar o bloqueio pelo celular:

1. Defina as variáveis de ambiente ou preencha diretamente na barra lateral do aplicativo:
* `TELEGRAM_BOT_TOKEN`: Token obtido através do `@BotFather`.
* `TELEGRAM_ALLOWED_USER_ID`: Seu ID de usuário no Telegram (obtenha via `@userinfobot`).


2. Quando um ataque for detectado, o sistema enviará um card com o botão **🔥 Bloquear IP Agora**, que executará o script de firewall diretamente no servidor remoto via SSH.

---

## 📄 Licença e Uso

Este projeto foi desenvolvido como uma solução de defesa cibernética enterprise autônoma. Sinta-se à vontade para utilizar, personalizar e expandir.

---

*VanguardSec AI v1.0 — Developed by [David Nonato*](https://github.com/DavidNonato23)

```

