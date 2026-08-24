import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def gerar_relatorio_pdf(scan_data):
    pasta_relatorios = "relatorios"
    os.makedirs(pasta_relatorios, exist_ok=True)

    timestamp_arquivo = scan_data["data"].replace(":", "-").replace(" ", "_")
    nome_arquivo = f"VanguardSec_Report_{scan_data['host']}_{timestamp_arquivo}.pdf"
    caminho_completo = os.path.join(pasta_relatorios, nome_arquivo)

    doc = SimpleDocTemplate(
        caminho_completo,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=12
    )

    story = [
        Paragraph(f"🛡️ Relatório Executivo SOC — {scan_data['host']}", title_style),
        Paragraph(f"<b>Data:</b> {scan_data['data']} | <b>Plataforma:</b> {scan_data['so']}", styles['Normal']),
        Spacer(1, 15),
        Paragraph("<b>🔍 Diagnóstico do Agente Auditor</b>", styles['Heading2']),
        Paragraph(scan_data['auditoria'].replace("\n", "<br/>"), styles['Normal']),
        Spacer(1, 15),
        Paragraph("<b>⚖️ Scorecard & Compliance</b>", styles['Heading2']),
        Paragraph(scan_data['compliance'].replace("\n", "<br/>"), styles['Normal']),
        Spacer(1, 15),
        Paragraph("<b>🛠️ Script de Remediação Validado</b>", styles['Heading2']),
        Paragraph(f"<pre>{scan_data['remediacao']}</pre>", styles['Code'])
    ]

    doc.build(story)
    return caminho_completo