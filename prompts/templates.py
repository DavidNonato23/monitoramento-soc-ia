PROMPTS_AUDITOR = {
    "ssh_brute_force": """Analise a telemetria: Logins falhos: {logins_falhos}, IP: {ip_atacante}.
Formato de saída:
* **Status:** ATAQUE EM ANDAMENTO
* **Ameaça:** Força Bruta via SSH detectada do IP {ip_atacante}.
* **Risco:** Alto risco de comprometimento de credenciais.""",

    "porta_db_exposta": """Analise a telemetria: Portas abertas de banco de dados sem firewall.
Formato de saída:
* **Status:** EXPOSIÇÃO DE SERVIÇO
* **Ameaça:** Banco de dados exposto publicamente na internet.
* **Risco:** Acesso não autorizado a dados sensíveis.""",

    "sistema_seguro": """Analise a telemetria: Logins falhos: 0, Portas expostas: 0.
Formato de saída:
* **Status:** SISTEMA OPERACIONAL
* **Ameaça:** Nenhuma anomalia crítica detectada.
* **Risco:** Baixo."""
}

PROMPTS_COMPLIANCE = {
    "lgpd_forca_bruta": """Avalie a conformidade da ameaça de Força Bruta SSH.
Formato de saída:
* **Nível de Risco:** CRÍTICO
* **Impacto LGPD:** Violação do Art. 46 (Falta de medidas técnicas para proteger dados pessoais).
* **Ação Exigida:** Bloqueio imediato da origem.""",

    "lgpd_banco_exposto": """Avalie a conformidade da exposição de porta de Banco de Dados.
Formato de saída:
* **Nível de Risco:** CRÍTICO
* **Impacto LGPD:** Violação do Art. 48 e Art. 46 (Exposição de dados sensíveis).
* **Ação Exigida:** Fechamento da porta externa e uso obrigatório de VPN.""",

    "compliance_ok": """Avalie a conformidade do servidor sem incidentes.
Formato de saída:
* **Nível de Risco:** BAIXO
* **Impacto LGPD:** Em conformidade com o Art. 46."""
}

PROMPTS_REMEDIACAO = {
    "bloqueio_ufw": """Ação recomendada para conter o invasor {ip_atacante}:
Ação: BLOQUEAR_UFW
Comando: sudo ufw deny from {ip_atacante} to any""",

    "bloqueio_windows": """Ação recomendada para conter o invasor {ip_atacante}:
Ação: BLOQUEAR_WINDOWS
Comando: New-NetFirewallRule -DisplayName "Bloqueio Invasor {ip_atacante}" -Direction Inbound -RemoteAddress {ip_atacante} -Action Block""",

    "kill_process": """Ação recomendada para conter processo suspeito:
Ação: KILL_PROCESS
Comando: sudo pkill -f nc""",

    "scan_portas": """Ação recomendada para mapeamento:
Ação: SCAN_PORTAS
Comando: ss -tuln"""
}