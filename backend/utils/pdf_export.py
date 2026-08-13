"""
PDF诊断报告导出模块
使用reportlab的platypus框架生成带中文的专业诊断报告PDF
"""
import os
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether
)
from reportlab.lib import colors
from reportlab.platypus.flowables import HRFlowable
from utils.file_util import get_unique_save_path

# ── 字体注册 ──
_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"
_CN = "Helvetica"  # 无中文字体时英文Fallback

def _register_chinese_font():
    global _FONT_REGISTERED, _FONT_NAME, _CN
    if _FONT_REGISTERED:
        return True
    candidates = [
        ("C:/Windows/Fonts/msyh.ttc", "MicrosoftYaHei"),
        ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
        ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSans"),
        ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
        ("simhei.ttf", "SimHei"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", path))
                _FONT_REGISTERED = True
                _FONT_NAME = "ChineseFont"
                _CN = "ChineseFont"
                return True
            except Exception:
                continue
    # 兜底：reportlab 内置 Adobe 宋体（CID 字体，无需外部字体文件）。
    # 容器/无字体环境（如 fonts-noto-cjk 的 CFF 轮廓不被 TTFont 支持）下保证中文可渲染
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        _FONT_REGISTERED = True
        _FONT_NAME = "STSong-Light"
        _CN = "STSong-Light"
        return True
    except Exception:
        return False

_register_chinese_font()

# ── 配色方案 ──
PRIMARY = colors.HexColor("#1a5276")       # 深蓝
PRIMARY_LIGHT = colors.HexColor("#2980b9") # 亮蓝
ACCENT = colors.HexColor("#e74c3c")        # 红色强调
BG_LIGHT = colors.HexColor("#f8f9fa")      # 浅灰背景
BORDER = colors.HexColor("#dee2e6")        # 边框色
TEXT_DARK = colors.HexColor("#2c3e50")     # 主文字色
TEXT_MUTED = colors.HexColor("#7f8c8d")    # 次要文字色
DIVIDER = colors.HexColor("#e9ecef")       # 分隔线色


def _make_section_header(title: str, accent_color=PRIMARY):
    """生成带左色条的章节标题"""
    bar = Table([[""]], colWidths=[3*mm], rowHeights=[22])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), accent_color),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    title_para = Paragraph(
        title,
        ParagraphStyle("SectionTitle", fontName=_CN, fontSize=13,
                       leading=22, textColor=accent_color,
                       alignment=TA_LEFT, leftIndent=4*mm)
    )
    row = Table([[bar, title_para]], colWidths=[3*mm, None])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return row


def _make_info_table(data: list, col_widths: list):
    """生成统一风格的信息表格"""
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), _CN),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    # 交替行背景
    for i in range(1, len(data)):
        if i % 2 == 1:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), BG_LIGHT))
    t.setStyle(TableStyle(style_cmds))
    return t


def generate_diagnosis_pdf(save_sub_dir: str, report_info: dict):
    """
    生成诊断报告PDF
    :param save_sub_dir: 存储子文件夹
    :param report_info: {
        patient_name, record_text, image_analysis, diagnosis_suggest
    }
    :return: (本地文件路径, 数据库存储相对路径)
    """
    full_path, rel_path = get_unique_save_path(save_sub_dir, "诊断报告.pdf")

    doc = SimpleDocTemplate(
        full_path, pagesize=A4,
        topMargin=1.8*cm, bottomMargin=1.8*cm,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
    )

    style_content = ParagraphStyle(
        "Content", fontName=_CN, fontSize=10, leading=17,
        alignment=TA_JUSTIFY, textColor=TEXT_DARK,
        spaceBefore=1*mm, spaceAfter=3*mm,
    )
    style_small = ParagraphStyle(
        "Small", fontName=_CN, fontSize=8.5, leading=13,
        alignment=TA_LEFT, textColor=TEXT_MUTED,
    )

    elements = []

    # ════════════════════════════════════════
    # 顶部蓝色标题区
    # ════════════════════════════════════════
    header_table = Table([
        [Paragraph(
            "AI 智慧医疗辅助诊断报告",
            ParagraphStyle("MainTitle", fontName=_CN, fontSize=16,
                           leading=24, textColor=colors.white,
                           alignment=TA_CENTER)
        )],
        [Paragraph(
            "AI Medical Diagnosis Report",
            ParagraphStyle("EnTitle", fontName="Helvetica", fontSize=10,
                           leading=14, textColor=colors.HexColor("#d5e8f5"),
                           alignment=TA_CENTER)
        )],
    ], colWidths=[16*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        # 底部圆角效果用浅色线替代
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))

    # ════════════════════════════════════════
    # 报告元信息
    # ════════════════════════════════════════
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    meta_data = [
        ["报告编号", f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
         "生成日期", now_str],
        ["患者姓名", report_info.get("patient_name", "未知"),
         "报告类型", "AI辅助诊断报告"],
    ]
    meta_table = _make_info_table(meta_data, [2.8*cm, 5.2*cm, 2.8*cm, 5.2*cm])
    elements.append(meta_table)
    elements.append(Spacer(1, 6*mm))

    # ════════════════════════════════════════
    # 内容分节
    # ════════════════════════════════════════
    sections = [
        ("一、病历摘要", report_info.get("record_text", ""),
         report_info.get("image_analysis", "")),
    ]

    for title, record_text, _ in sections:
        if not record_text:
            continue
        elements.append(_make_section_header(title, PRIMARY))
        elements.append(Spacer(1, 2*mm))
        safe = record_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elements.append(Paragraph(safe, style_content))
        elements.append(Spacer(1, 3*mm))

    # 影像分析（单独处理，没有时显示占位）
    img_analysis = report_info.get("image_analysis", "")
    if img_analysis:
        elements.append(_make_section_header("二、影像分析结果", PRIMARY_LIGHT))
        elements.append(Spacer(1, 2*mm))
        safe = img_analysis.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elements.append(Paragraph(safe, style_content))
        elements.append(Spacer(1, 3*mm))
    else:
        elements.append(_make_section_header("二、影像分析结果", PRIMARY_LIGHT))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "暂无影像分析数据",
            ParagraphStyle("NoData", fontName=_CN, fontSize=10,
                           leading=16, textColor=TEXT_MUTED,
                           alignment=TA_LEFT, leftIndent=2*mm)
        ))
        elements.append(Spacer(1, 3*mm))

    # AI诊断建议（用红色强调色）
    diag = report_info.get("diagnosis_suggest", "")
    if diag:
        elements.append(_make_section_header("三、AI 诊断建议", ACCENT))
        elements.append(Spacer(1, 2*mm))
        safe = diag.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elements.append(Paragraph(safe, style_content))
        elements.append(Spacer(1, 3*mm))

    # ════════════════════════════════════════
    # 免责声明（红框）
    # ════════════════════════════════════════
    elements.append(Spacer(1, 8*mm))
    disclaimer_text = (
        "免责声明：本报告由人工智能系统自动生成，仅供参考，不构成医疗诊断或治疗建议。"
        "最终诊断结果请以临床医师的判断为准。"
    )
    disc_table = Table(
        [[Paragraph(
            f"<b>{disclaimer_text}</b>",
            ParagraphStyle("Disc", fontName=_CN, fontSize=8,
                           leading=13, textColor=ACCENT,
                           alignment=TA_CENTER)
        )]],
        colWidths=[16*cm]
    )
    disc_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf2f2")),
    ]))
    elements.append(disc_table)

    # ════════════════════════════════════════
    # 页脚（页码 + 系统名）
    # ════════════════════════════════════════
    def add_page_number(canvas_obj, doc_obj):
        canvas_obj.saveState()
        # 页脚线
        canvas_obj.setStrokeColor(DIVIDER)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(2.2*cm, 1.3*cm, A4[0]-2.2*cm, 1.3*cm)
        # 页码
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(TEXT_MUTED)
        canvas_obj.drawCentredString(
            A4[0] / 2, 0.9*cm,
            f"- {doc_obj.page} -"
        )
        canvas_obj.drawRightString(
            A4[0] - 2.2*cm, 0.9*cm,
            "Medical AI System"
        )
        canvas_obj.drawString(
            2.2*cm, 0.9*cm,
            datetime.now().strftime("%Y-%m-%d")
        )
        canvas_obj.restoreState()

    # ── 构建 ──
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return full_path, rel_path
