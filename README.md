O `README.md` acima foi resumido ao máximo para atender estritamente ao pedido do seu gestor de **"tirar palavras difíceis e ser bastante objetivo"**.

No entanto, em um projeto completo do porte da **versão v1.4 do VanguardSec AI**, simplificar demais pode acabar escondendo funcionalidades importantes que enriquecem o produto.

Se você acha que ficou enxuto demais, aqui está a **versão intermediária perfeita**: ela mantém a linguagem direta, limpa e sem palavras difíceis, mas reintroduz as seções técnicas cruciais (como as imagens de evidência, a tabela do painel web, a arquitetura visual e os destaques do produto):

---

# 🛡️ VanguardSec AI — Plataforma Autônoma SOC, SOAR & Active Defense

Plataforma de segurança cibernética que monitora servidores Linux e Windows Server em tempo real, analisa ataques de invasão usando Inteligência Artificial local (**Ollama / `qwen2.5:3b**`), bloqueia os atacantes automaticamente no firewall e gera laudos executivos em PDF para auditoria (LGPD e ISO 27001).

---

## 🎯 O que o sistema faz

* **Monitoramento Sem Agente (Agentless):** Conecta via SSH (Linux) e WinRM (Windows Server) para ler logs em tempo real sem precisar instalar nada no servidor alvo.
* **Análise por IA Local:** Processa os logs usando o modelo local `qwen2.5:3b`, identificando a gravidade do ataque e enquadrando na LGPD (Art. 46) e ISO 27001.
* **Bloqueio Automático no Firewall (SOAR):** Aplica regras de bloqueio no `UFW` e encerra sessões ativas do atacante instantaneamente.
* **Geolocalização & Defesa Ativa:** Descobre a origem do IP invasor (País, Cidade e Provedor) e executa varredura reversa de portas no computador do atacante.
* **Laudos Executivos em PDF:** Gera relatórios automáticos formatados com a marca da empresa na pasta `relatorios_pdf/`.
* **Painel Web & Threat Intel:** Interface gráfica em Streamlit (`localhost:8501`) com gráficos em tempo real e integração com a base global de ameaças da **CISA KEV**.

---

## 🧩 Módulos do Painel Web

| Módulo | O que ele exibe / faz |
| --- | --- |
| 📈 **Dashboard Executivo** | Uso de CPU, RAM, disco do servidor e tentativas de ataque nas últimas 24h. |
| 🔬 **Esteira Multi-Tier** | Parecer detalhado dos 3 Agentes de IA (SOC, Compliance e SOAR). |
| 🌐 **Monitoramento Infra** | Análise de rede, nível de risco e origem do tráfego do servidor. |
| 🛡️ **Playbooks SOAR** | Comandos e regras de bloqueio prontos para execução. |
| 📂 **Gestão de Incidentes** | Lista de ataques com opção de **Kill Switch** (bloquear IP em 1 clique). |
| 📱 **Painel ChatOps** | Configuração do Bot do Telegram para alertas e comandos no celular. |
| 📄 **Centro de Relatórios** | Histórico e download dos laudos em PDF gerados pelo sistema. |
| 📡 **Cyber Threat Intelligence** | Dados brutos coletados e comparação ao vivo com o feed global CISA KEV. |

---

## 🎨 Principais Destaques

* **Privacidade Absoluta (100% On-Premise):** A IA roda totalmente local via Ollama. Nenhum log ou dado da sua empresa é enviado para APIs na nuvem.
* **Suporte Dual-Platform:** Monitora servidores Ubuntu (Linux) e Windows Server no mesmo painel.
* **Kill Switch de Emergência:** Botões de contenção imediata no painel para bloquear IPs ou reiniciar o serviço SSH com um clique.
* **ChatOps via Telegram:** Receba notificações de ataques no celular com botões para aprovar o bloqueio do atacante.
* **Exportação para Power BI:** Salva dados no banco SQLite (`vanguard_sec.db`) e em CSV UTF-8 (`vanguard_powerbi_data.csv`).

---

## 📂 Estrutura do Repositório

```text
VanguardSec-AI/
├── agentes/               # Módulos de IA (Tier 1 SOC, Tier 2 Compliance, Tier 3 SOAR)
├── modulos/               # Coletores SSH/WinRM, GeoIP, Active Defense e PDF
├── politicas/             # Documentos ISO 27001 e LGPD para a IA consultar
├── relatorios_pdf/        # Laudos executivos gerados em PDF
├── scripts/               # Scripts de teste e validação de prompts
├── engine.py              # Motor principal de monitoramento e defesa
├── app.py                 # Interface do Painel Web (Streamlit)
├── cti_dashboard.py       # Painel de inteligência de ameaças e CISA KEV
└── requirements.txt       # Lista de bibliotecas necessárias

```

---

## 🛠️ Pré-requisitos

* **Sistema Operacional:** Windows, Linux ou macOS.
* **Python:** Versão 3.10 ou superior.
* **Ollama Engine:** Instalado rodando o modelo `qwen2.5:3b`.
* **Servidor Alvo Linux:** Ubuntu com SSH ativo e permissão de `sudo ufw`.
* **Servidor Alvo Windows (Opcional):** Windows Server com WinRM habilitado na porta 5985.

---

## 🚀 Como Instalar e Rodar

### 1. Clonar o repositório e criar ambiente virtual

```bash
git clone https://github.com/DavidNonato23/vanguardsec-ai.git
cd vanguardsec-ai

# Criar ambiente virtual
python -m venv venv

# Ativar no Windows (PowerShell)
.\venv\Scripts\activate

# Ativar no Linux/macOS
source venv/bin/activate

```

### 2. Instalar dependências e baixar a IA

```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b

```

### 3. Iniciar o sistema

* **Para rodar o motor de monitoramento:**
```bash
python engine.py

```


* **Para abrir o Painel Web no navegador (`http://localhost:8501`):**
```bash
streamlit run app.py

```



---

## 📱 ChatOps via Telegram (Opcional)

Para receber alertas no celular:

1. Insira seu `TELEGRAM_BOT_TOKEN` e `TELEGRAM_ALLOWED_USER_ID` no arquivo `.env` ou pela aba **Painel ChatOps** na interface Web.
2. Clique no botão de teste para validar o envio de mensagens interativas.

---

## 👨‍💻 Autor e Desenvolvedor

**Idealização, Arquitetura & Engenharia:** David Nonato

* **GitHub:** [@DavidNonato23](https://github.com/DavidNonato23)