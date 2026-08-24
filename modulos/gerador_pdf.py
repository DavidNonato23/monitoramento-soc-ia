import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def gerar_relatorio_pdf(scan_data):
    """Gera um relatório PDF executivo com os resultados do scan e salvamento em /relatorios/."""
    os.makedirs("relatorios", exist_ok=True)
    file_path = f"relatorios/Relatorio_SOC_{scan_data['host'].replace('.', '_')}.pdf"

    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E293B'))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#0F172A'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#334155'))

    story.append(Paragraph("🛡️ VanguardSec AI — Relatório Executivo de SOC", title_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1')))
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"<b>Data da Coleta:</b> {scan_data['data']}", body_style))
    story.append(Paragraph(f"<b>Ativo Auditado:</b> {scan_data['host']} ({scan_data['so']})", body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("🔍 Diagnóstico do Agente Auditor", h2_style))
    story.append(Paragraph(scan_data['auditoria'].replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("⚖️ Compliance & Normas (ISO 17021)", h2_style))
    story.append(Paragraph(scan_data['compliance'].replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("🛠️ Script de Remediação Proposto", h2_style))
    story.append(Paragraph(f"<font face='Courier'>{scan_data['remediacao'].replace('\n', '<br/>')}</font>", body_style))

    doc.build(story)
    return file_path   # ✅ Correto