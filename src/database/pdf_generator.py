import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def gerar_relatorio_pdf(dados_incidente: dict, caminho_saida_pdf: str) -> str:
    doc = SimpleDocTemplate(
        caminho_saida_pdf,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    story = []

    # 1. Cabeçalho com Logo do Cliente e Título
    logo_path = dados_incidente["cabecalho"].get("logo_path", "")
    
    # Estilo de Títulos
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1A2B4C'))
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, textColor=colors.gray)
    
    header_data = []
    text_header = Paragraph(
        f"<b>RELATÓRIO DE INCIDENTE E RESPOSTA AUTÔNOMA</b><br/>"
        f"<font size=9 color='gray'>VanguardSec AI — Plataforma SOC/SOAR</font>", 
        title_style
    )
    
    if logo_path and os.path.exists(logo_path):
        img = Image(logo_path, width=120, height=40)
        header_table = Table([[img, text_header]], colWidths=[130, 410])
    else:
        header_table = Table([[text_header]], colWidths=[540])

    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(header_table)
    story.append(Spacer(1, 15))

    # 2. Tabela de Resumo do Incidente
    meta_info = [
        [Paragraph("<b>ID Incidente:</b>", styles['Normal']), dados_incidente["cabecalho"]["id_incidente"],
         Paragraph("<b>Data/Hora:</b>", styles['Normal']), dados_incidente["cabecalho"]["data_hora"]],
        [Paragraph("<b>Servidor Alvo:</b>", styles['Normal']), dados_incidente["cabecalho"]["origem_evento"],
         Paragraph("<b>IP Atacante:</b>", styles['Normal']), dados_incidente["dados_evento"]["ip_atacante"]],
        [Paragraph("<b>Severidade:</b>", styles['Normal']), 
         Paragraph(f"<font color='red'><b>{dados_incidente['parecer_agentes']['tier1_soc']['severidade']}</b></font>", styles['Normal']),
         Paragraph("<b>Status SOAR:</b>", styles['Normal']), "Mitigado Automatizado"]
    ]
    
    t_meta = Table(meta_info, colWidths=[90, 180, 90, 180])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F4F6F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # 3. Análise dos Agentes por Tier
    def adicionar_secao(titulo, cor_hex, conteudo_list):
        story.append(Paragraph(f"<b><font color='{cor_hex}'>{titulo}</font></b>", styles['Heading2']))
        story.append(Spacer(1, 4))
        for item in conteudo_list:
            story.append(Paragraph(item, styles['Normal']))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 10))

    # Tier 1 SOC
    adicionar_secao("🔍 Tier 1 — Análise Telemétrica (Analista SOC)", "#0056B3", [
        f"<b>Parecer Técnico:</b> {dados_incidente['parecer_agentes']['tier1_soc']['parecer']}",
        f"<b>Recomendação:</b> {dados_incidente['parecer_agentes']['tier1_soc']['recomendacao']}"
    ])

    # Tier 2 Compliance
    adicionar_secao("⚖️ Tier 2 — Impacto Regulatório (ISO 27001 & LGPD)", "#7B2CBF", [
        f"<b>Enquadramento LGPD:</b> {dados_incidente['parecer_agentes']['tier2_compliance']['artigo_lgpd']}",
        f"<b>Controle ISO 27001:</b> {dados_incidente['parecer_agentes']['tier2_compliance']['controle_iso']}",
        f"<b>Avaliação de Risco:</b> {dados_incidente['parecer_agentes']['tier2_compliance']['risco_normativo']}"
    ])

    # Tier 3 SOAR
    adicionar_secao("🛡️ Tier 3 — Contenção e Resposta Autônoma (SOAR)", "#D90429", [
        f"<b>Comando de Mitigação:</b> <code>{dados_incidente['parecer_agentes']['tier3_soar']['comando_executado']}</code>",
        f"<b>Resultado da Ação:</b> {dados_incidente['parecer_agentes']['tier3_soar']['status_acao']}"
    ])

    # 4. Log Bruto de Evidência
    story.append(Paragraph("<b>📋 Evidência Telemétrica (Log Bruto):</b>", styles['Heading3']))
    t_log = Table([[Paragraph(f"<font size=8 color='darkgray'>{dados_incidente['dados_evento']['log_bruto']}</font>", styles['Normal'])]], colWidths=[540])
    t_log.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E1E1E')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_log)

    doc.build(story)
    return caminho_saida_pdf