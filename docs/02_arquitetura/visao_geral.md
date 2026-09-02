# 🏗️ Arquitetura de Software & Desenho Modular

## 1. Princípios de Engenharia
A solução segue a **Separação de Responsabilidades (SoC)** com **Desacoplamento Fraco (Loose Coupling)**:
* **`src/telemetry`:** Ingestão limpa e parsing de logs SSH/Paramiko.
* **`src/ai`:** Orquestração de modelos de IA de forma agnóstica (OpenAI / Ollama).
* **`src/soar`:** Execução isolada de regras de firewall (`UFW`) e *Kill Switch*.
* **`src/database`:** Persistência em SQLite e exportação para analytics (CSV).

## 2. Abstração de Provedor de IA (LLM Provider Agnostic)
A engine alterna dinamicamente entre serviços na nuvem (Azure OpenAI / OpenAI) e execução local (Ollama/Qwen) com base em variáveis de ambiente (`LLM_PROVIDER`), garantindo flexibilidade para clientes Enterprise.