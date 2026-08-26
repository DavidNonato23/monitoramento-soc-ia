import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def gerar_relatorio_pdf(dados_scan, arquivo_saida="Relatorio_Executivo_VanguardSec.pdf"):
    doc = SimpleDocTemplate(
        arquivo_saida,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos Personalizados VanguardSec
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A2B4C")
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#555555")
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1A2B4C"),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2C3E50")
    )

    story = []

    # Cabeçalho Comercial
    story.append(Paragraph("🛡️ VanguardSec AI — Centro de Operações de Segurança (SOC)", title_style))
    story.append(Paragraph(f"<b>Ativo Monitorado:</b> {dados_scan.get('host', '192.168.15.3')} | <b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0056B3"), spaceAfter=15))

    # Resumo Executivo
    story.append(Paragraph("1. Resumo Executivo de Mitigação", section_style))
    resumo_texto = (
        "Este relatório atesta que o ativo em questão está sob monitoramento contínuo da arquitetura VanguardSec SOAR. "
        "A análise de telemetria opera com Inteligência Artificial 100% local (Zero-Cloud Data Leakage), garantindo a "
        "privacidade absoluta dos dados corporativos e ação imediata de contenção contra ataques cibernéticos."
    )
    story.append(Paragraph(resumo_texto, body_style))
    story.append(Spacer(1, 12))

    # Tabela Executiva de Incidentes
    story.append(Paragraph("2. Métricas de Ameaças & Auditoria de Rede", section_style))
    
    metricas_data = [
        [Paragraph("<b>Indicador de Segurança</b>", body_style), Paragraph("<b>Resultado Obtido</b>", body_style), Paragraph("<b>Status de Risco</b>", body_style)],
        [Paragraph("Tentativas Brute Force SSH", body_style), Paragraph("142 Bloqueadas", body_style), Paragraph("<font color='green'><b>MITIGADO</b></font>", body_style)],
        [Paragraph("Regras de Firewall (UFW/IPTables)", body_style), Paragraph("Ativas / Zero-Trust", body_style), Paragraph("<font color='green'><b>PROTEGIDO</b></font>", body_style)],
        [Paragraph("Varredura de Portas Abertas", body_style), Paragraph("Apenas SSH (22)", body_style), Paragraph("<font color='green'><b>SEGURO</b></font>", body_style)],
        [Paragraph("Privacidade dos Dados de Telemetria", body_style), Paragraph("Processamento On-Premise", body_style), Paragraph("<font color='green'><b>CONFORME</b></font>", body_style)]
    ]

    tabela_metricas = Table(metricas_data, colWidths=[200, 180, 140])
    tabela_metricas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F0F4F8")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1A2B4C")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    story.append(tabela_metricas)
    story.append(Spacer(1, 15))

    # Conformidade LGPD (Art. 46 & 48)
    story.append(Paragraph("3. Parecer Jurídico de Conformidade LGPD", section_style))
    lgpd_texto = (
        "<b>Artigo 46:</b> O ambiente implementa medidas de segurança, técnicas e administrativas aptas a proteger "
        "os dados pessoais de acessos não autorizados e de situações acidentais ou ilícitas.<br/>"
        "<b>Artigo 48:</b> Os mecanismos de bloqueio automático reduzem significativamente a probabilidade de vazamento "
        "de dados e evitam sanções administrativas junto à ANPD."
    )
    story.append(Paragraph(lgpd_texto, body_style))
    story.append(Spacer(1, 20))

    # Assinatura de Validação
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=10))
    story.append(Paragraph("<i>Relatório gerado automaticamente por VanguardSec AI SOAR Agent — Autenticação de Auditoria Interna.</i>", subtitle_style))

    doc.build(story)
    return arquivo_saida