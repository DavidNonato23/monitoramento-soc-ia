import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PASTA_RELATORIOS = "relatorios"

def gerar_relatorio_pdf(scan_data):
    """
    Gera um relatório executivo em PDF unificado contendo métricas, 
    o gráfico do dashboard embutido e os pareceres das IAs.
    """
    if not os.path.exists(PASTA_RELATORIOS):
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)

    timestamp_arquivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    host_limpo = scan_data.get('host', 'ativo').replace('.', '_')
    nome_pdf = f"Relatorio_SOC_{host_limpo}_{timestamp_arquivo}.pdf"
    caminho_pdf = os.path.join(PASTA_RELATORIOS, nome_pdf)

    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E293B")
    )
    
    style_subtitulo = ParagraphStyle(
        'SubtituloDoc',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B")
    )

    style_secao = ParagraphStyle(
        'SecaoDoc',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=10,
        spaceAfter=6
    )

    style_body = ParagraphStyle(
        'BodyDoc',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    style_code = ParagraphStyle(
        'CodeDoc',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        backColor=colors.HexColor("#F8FAFC"),
        borderColor=colors.HexColor("#E2E8F0"),
        borderWidth=1,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=4
    )

    # Cabeçalho
    story.append(Paragraph("🛡️ VanguardSec AI — Relatório Executivo de Segurança", style_titulo))
    story.append(Paragraph(f"Ativo Monitorado: <b>{scan_data.get('host', 'N/A')}</b> ({scan_data.get('so', 'Linux')}) | Gerado em: {scan_data.get('data', 'N/A')}", style_subtitulo))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=12))

    # Tabela de Métricas
    m_raw = scan_data.get("metricas", {})
    info_r = scan_data.get("info_rede", {})

    dados_tabela = [
        ["Classificação de Rede", "Nível de Risco", "Logins Falhos (24h)", "Conexões TCP", "Portas Expostas"],
        [
            info_r.get("tipo_rede", "N/A"),
            info_r.get("nivel_risco_origem", "Baixo"),
            str(m_raw.get("logins_falhos", "0")),
            str(m_raw.get("conexoes_estab", "0")),
            str(m_raw.get("portas_abertas", "0"))
        ]
    ]

    tabela_kpi = Table(dados_tabela, colWidths=[110, 90, 110, 95, 95])
    tabela_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F1F5F9")),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor("#1E293B")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    
    story.append(tabela_kpi)
    story.append(Spacer(1, 14))

    # Gráfico Dashboard embutido (Verificação de segurança da imagem)
    caminho_grafico = scan_data.get("caminho_grafico")
    if caminho_grafico and os.path.exists(caminho_grafico):
        story.append(Paragraph("<b>📈 Telemetria de Volumetria e Eventos em Tempo Real</b>", style_secao))
        story.append(Spacer(1, 4))
        story.append(Image(caminho_grafico, width=520, height=180))
        story.append(Spacer(1, 12))

    # Pareceres IA
    story.append(Paragraph("<b>🌐 Diagnóstico de Tráfego de Rede (NTA)</b>", style_secao))
    story.append(Paragraph(scan_data.get("analise_trafego_ia", "Nenhum dado registrado.").replace("\n", "<br/>"), style_body))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>⚖️ Aderência e Risco de Compliance (LGPD / ISO 27001)</b>", style_secao))
    story.append(Paragraph(scan_data.get("compliance", "Nenhum dado registrado.").replace("\n", "<br/>"), style_body))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>🛠️ Playbook Automático de Remediação (SOAR)</b>", style_secao))
    script_rem = scan_data.get("remediacao", "# Nenhum playbook gerado").replace("\n", "<br/>")
    story.append(Paragraph(f"<code>{script_rem}</code>", style_code))

    doc.build(story)
    return caminho_pdf