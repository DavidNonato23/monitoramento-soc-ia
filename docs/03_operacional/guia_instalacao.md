# 🛠️ Guia Prático de Implantação On-Premise & Cloud

## 1. Requisitos Mínimos de Sistema
* **SO:** Ubuntu Server 22.04 LTS ou superior.
* **Hardware:** 4 Cores CPU, 8GB RAM (para Ollama local) ou 2 Cores CPU, 2GB RAM (para uso via API OpenAI).
* **Dependências:** Python 3.10+, UFW ativo e credenciais SSH do servidor alvo.

## 2. Passo a Passo de Execução
1. Execute o script de preparação do ambiente:
   ```bash
   bash scripts/setup.sh