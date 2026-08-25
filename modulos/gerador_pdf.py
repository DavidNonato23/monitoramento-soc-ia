import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def gerar_relatorio_pdf(scan_data):
    """Gera relatório PDF executivo com design estruturado."""
    os.makedirs("relatorios", exist_ok=True)
    file_path = f"relatorios/Relatorio_SOC_{scan_data['host'].replace('.', '_').replace(' ', '_')}.pdf"

    doc = SimpleDocTemplate(
        file_path, 
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#0F172A'), spaceAfter=4)
    subtitle_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#475569'), spaceAfter=10)
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#1E293B'), spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#334155'))
    code_style = ParagraphStyle('CodeStyle', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=10, textColor=colors.HexColor('#0F172A'))

    # Cabeçalho
    story.append(Paragraph("🛡️ VanguardSec AI — Security Operations Center (SOC)", title_style))
    story.append(Paragraph("Relatório Técnico de Incidente & Análise de Conformidade Automática (SOAR)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=10))

    # Tabela Resumo
    metricas = scan_data.get("metricas", {})
    table_data = [
        [Paragraph("<b>Ativo Auditado:</b>", body_style), Paragraph(f"{scan_data['host']} ({scan_data['so']})", body_style)],
        [Paragraph("<b>Data/Hora da Análise:</b>", body_style), Paragraph(scan_data['data'], body_style)],
        [Paragraph("<b>Tentativas de Força Bruta:</b>", body_style), Paragraph(f"<font color='red'><b>{metricas.get('logins_falhos', '0')} Falhas</b></font>", body_style)],
        [Paragraph("<b>Conexões TCP Estabelecidas:</b>", body_style), Paragraph(f"{metricas.get('conexoes_estab', '0')} Conexões", body_style)],
        [Paragraph("<b>Portas de Serviço Expostas:</b>", body_style), Paragraph(f"{metricas.get('portas_abertas', '0')} Listening", body_style)],
    ]

    t = Table(table_data, colWidths=[160, 380])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Diagnóstico da IA
    story.append(Paragraph("🧠 Diagnóstico Técnico (Qwen2.5-Coder Engine)", h2_style))
    story.append(Paragraph(scan_data['auditoria'].replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 8))

    # Compliance
    story.append(Paragraph("⚖️ Scorecard de Compliance (ISO 27001 / LGPD)", h2_style))
    story.append(Paragraph(scan_data['compliance'].replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 8))

    # Playbook SOAR
    story.append(Paragraph("🛠️ Playbook Executável de Contenção (SOAR)", h2_style))
    script_table = Table([[Paragraph(scan_data['remediacao'].replace('\n', '<br/>'), code_style)]], colWidths=[540])
    script_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(script_table)
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=6))
    story.append(Paragraph("Documento Confidencial — VanguardSec Autonomous Threat Response Pipeline", subtitle_style))

    doc.build(story)
    return file_path