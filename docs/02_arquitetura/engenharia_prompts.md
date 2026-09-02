# 🤖 Engenharia de Prompts & Benchmark de Performance

## 1. Estrutura por Tiers
* **Tier 1 (SOC):** Temperatura `0.1` | Foco em velocidade e estrita validação de formato.
* **Tier 2 (Compliance):** Temperatura `0.3` | Análise regulatória de impacto sob a LGPD e ISO 27001.
* **Tier 3 (SOAR):** Temperatura `0.0` | Geração estrita de comandos Bash determinísticos sem alucinação.

## 2. Boas Práticas Implementadas
* **Guardrails de Segurança:** Instruções explícitas contra *Prompt Injection* dentro dos logs.
* **Few-Shot Prompting:** Exemplos de entrada e saída em JSON fornecidos no próprio esquema.
* **Prompt Compression:** Prompts enxutos que reduzem o consumo de tokens em até 70%.