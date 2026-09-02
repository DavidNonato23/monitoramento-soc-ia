# 📄 Padrão de Relatórios Executivos & Personalização de Marca

## 1. Identidade Visual do Cliente (White-Label)
O módulo `src/database/pdf_generator.py` suporta personalização da marca para cada cliente contratante:
* **Logo Corporativa:** Inserida automaticamente no cabeçalho superior esquerdo (`assets/logo_cliente.png`).
* **Relatório Auditável:** Contém carimbo IP, Timestamp e Hash de integridade da evidência.

## 2. Estrutura do Laudo Gerado
1. **Cabeçalho Institucional:** Marca da empresa cliente + ID do Incidente.
2. **Resumo Executivo (Metadata):** Severidade do ataque, IP atacante, servidor afetado e status de mitigação.
3. **Seção Tier 1 (SOC):** Leitura de IoCs e gravidade.
4. **Seção Tier 2 (Compliance):** Artigos da LGPD e ISO 27001 violados.
5. **Seção Tier 3 (SOAR):** Comando Bash executado no firewall para bloqueio.
6. **Evidência Forense:** Log bruto registrado para fins de auditoria.