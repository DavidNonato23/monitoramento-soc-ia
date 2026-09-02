markdown
# 🔒 Conformidade LGPD (Lei Geral de Proteção de Dados)

## 1. Enquadramento no Artigo 46
O **VanguardSec AI** aplica medidas de segurança técnicas e administrativas aptas a proteger os dados pessoais de acessos não autorizados:
* **Privacidade por Design (Data Minimization):** Apenas logs de rede e IPs de origem são processados. Nenhum dado sensível de usuário é mantido sem necessidade.
* **Opção de Processamento Air-Gapped:** Quando executado via Ollama local, 0% dos logs trafegam pela internet, garantindo compliance total com políticas de privacidade corporativas.

## 2. Mapeamento de Controles ISO 27001
* **Controle A.8.2 (Classificação da Informação):** Logs auditados e rotulados por nível de severidade.
* **Controle A.12.6 (Gestão de Vulnerabilidades Técnicas):** Detecção autônoma de varreduras de porta e tentativas de invasão SSH.