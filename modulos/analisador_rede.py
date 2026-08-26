import json
import os
import csv
import ipaddress

class AnalisadorRede:
    def __init__(self, pasta_dados="modulos/dados"):
        self.pasta_dados = pasta_dados

    def classificar_ip(self, ip_str):
        """Identifica se o IP é da rede interna (privado) ou externo (público)."""
        if not ip_str or ip_str in ["127.0.0.1", "localhost"]:
            return "Localhost / Loopback", "Baixo"
            
        try:
            ip = ipaddress.ip_address(ip_str.strip())
            if ip.is_private:
                return "Privado (Rede Interna)", "Médio"
            return "Público (Externo)", "Crítico"
        except ValueError:
            return "IP Inválido", "Baixo"

    def buscar_cliente_por_ip(self, ip_alvo):
        """Cruza o IP auditado com a base clientes_com_ip.csv."""
        caminho_csv = os.path.join(self.pasta_dados, "clientes_com_ip.csv")
        if not os.path.exists(caminho_csv):
            return "Cliente Não Cadastrado"

        try:
            with open(caminho_csv, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("IP") == ip_alvo:
                        return row.get("Cliente", "Desconhecido")
        except Exception:
            pass
        return "Desconhecido / Externo"

    def enriquecer_diagnostico(self, ip_detectado):
        """Gera metadados do IP para enviar aos agentes de IA."""
        tipo_ip, nivel_risco = self.classificar_ip(ip_detectado)
        cliente = self.buscar_cliente_por_ip(ip_detectado)

        return {
            "ip": ip_detectado,
            "tipo_rede": tipo_ip,
            "nivel_risco_origem": nivel_risco,
            "proprietario_vinculado": cliente
        }