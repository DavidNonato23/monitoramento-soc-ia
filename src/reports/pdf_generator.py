import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PASTA_RELATORIOS = "./relatorios_pdf"

def salvar_relatorio_incidente(dados_incidente: dict) -> str:
    """
    Gera o laudo executivo em PDF na pasta relatorios_pdf/ organizado por mês.
    """
    agora = datetime.datetime.now()
    pasta_mes = os.path.join(PASTA_RELATORIOS, agora.strftime("%Y-%m"))
    os.makedirs(pasta_mes, exist_ok=True)

    id_incidente = dados_incidente["cabecalho"].get("id_incidente", "INC-000")
    nome_arquivo = f"{id_incidente}.pdf"
    caminho_pdf = os.path.join(pasta_mes, nome_arquivo)

    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    story = []

    # 1. Cabeçalho do Laudo
    logo_path = dados_incidente["cabecalho"].get("logo_path", "")
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1A2B4C'))
    
    text_header = Paragraph(
        f"<b>RELATÓRIO DE INCIDENTE & MITIGAÇÃO AUTÔNOMA</b><br/>"
        f"<font size=9 color='gray'>VanguardSec AI — Proteção Digital Privada</font>", 
        title_style
    )
    
    if logo_path and os.path.exists(logo_path):
        img = Image(logo_path, width=110, height=35)
        header_table = Table([[img, text_header]], colWidths=[120, 420])
    else:
        header_table = Table([[text_header]], colWidths=[540])

    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(header_table)
    story.append(Spacer(1, 15))

    # 2. Tabela Resumo do Incidente
    meta_info = [
        [Paragraph("<b>ID Incidente:</b>", styles['Normal']), dados_incidente["cabecalho"]["id_incidente"],
         Paragraph("<b>Data/Hora:</b>", styles['Normal']), dados_incidente["cabecalho"]["data_hora"]],
        [Paragraph("<b>Origem Alvo:</b>", styles['Normal']), dados_incidente["cabecalho"]["origem_evento"],
         Paragraph("<b>IP Atacante:</b>", styles['Normal']), dados_incidente["dados_evento"]["ip_atacante"]],
        [Paragraph("<b>Severidade:</b>", styles['Normal']), 
         Paragraph(f"<font color='red'><b>{dados_incidente['parecer_agentes']['tier1_soc']['severidade']}</b></font>", styles['Normal']),
         Paragraph("<b>Ação SOAR:</b>", styles['Normal']), "IP Bloqueado"]
    ]
    
    t_meta = Table(meta_info, colWidths=[90, 180, 90, 180])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F4F6F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # 3. Conteúdo dos Agentes por Tier
    styles_h2 = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=12, spaceAfter=4)
    
    story.append(Paragraph("<b><font color='#0056B3'>🔍 Tier 1 — Triagem Telemétrica (Analista SOC)</font></b>", styles_h2))
    story.append(Paragraph(f"<b>Parecer:</b> {dados_incidente['parecer_agentes']['tier1_soc']['parecer']}", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b><font color='#7B2CBF'>⚖️ Tier 2 — Impacto Regulatório (ISO 27001 & LGPD)</font></b>", styles_h2))
    story.append(Paragraph(f"<b>Enquadramento LGPD:</b> {dados_incidente['parecer_agentes']['tier2_compliance']['artigo_lgpd']}", styles['Normal']))
    story.append(Paragraph(f"<b>Controle ISO:</b> {dados_incidente['parecer_agentes']['tier2_compliance']['controle_iso']}", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b><font color='#D90429'>🛡️ Tier 3 — Resposta Autônoma (SOAR)</font></b>", styles_h2))
    story.append(Paragraph(f"<b>Comando Bash:</b> <code>{dados_incidente['parecer_agentes']['tier3_soar']['comando_executado']}</code>", styles['Normal']))
    story.append(Spacer(1, 12))

    # 4. Evidência Telemétrica (Log Bruto)
    story.append(Paragraph("<b>📋 Evidência Telemétrica (Log Bruto):</b>", styles['Heading3']))
    t_log = Table([[Paragraph(f"<font size=8 color='darkgray'>{dados_incidente['dados_evento']['log_bruto']}</font>", styles['Normal'])]], colWidths=[540])
    t_log.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E1E1E')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_log)

    doc.build(story)
    return caminho_pdf


def gerar_pdf_relatorio_auditoria_preventiva(dados_auditoria: dict, caminho_saida_pdf: str) -> str:
    """
    Gera um laudo executivo de Prontidão para Auditoria pronto para impressão.
    """
    doc = SimpleDocTemplate(
        caminho_saida_pdf,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho do Laudo de Auditoria
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1A2B4C'))
    story.append(Paragraph("<b>RELATÓRIO DE PRONTIDÃO PARA AUDITORIA DE SEGURANÇA</b>", title_style))
    story.append(Paragraph(f"<font size=9 color='gray'>Gerado em: {dados_auditoria.get('timestamp', '')} | VanguardSec AI</font>", styles['Normal']))
    story.append(Spacer(1, 15))

    # Tabela Status de Prontidão
    status = dados_auditoria.get("status_prontidao", "ATENCAO")
    cor_status = colors.green if status == "PRONTO" else colors.orange if status == "ATENCAO" else colors.red
    
    t_data = [
        [Paragraph("<b>Status da Empresa:</b>", styles['Normal']), Paragraph(f"<b><font color='{cor_status}'>{status}</font></b>", styles['Normal'])],
        [Paragraph("<b>Itens em Vencimento/Risco:</b>", styles['Normal']), Paragraph(dados_auditoria.get("itens_criticos_vencimento", "Nenhum"), styles['Normal'])],
        [Paragraph("<b>Recomendação Executiva:</b>", styles['Normal']), Paragraph(dados_auditoria.get("recomendacao_auditoria", "Manter rotina de inspeção."), styles['Normal'])]
    ]
    
    t = Table(t_data, colWidths=[160, 380])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    
    doc.build(story)
    return caminho_saida_pdf