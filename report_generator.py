"""
PDF 报告生成器
"""
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

# ── 默认占位数据（接口数据未传入时使用）────────────────────────────
_DEFAULTS = {
    # 结论
    'effective_ratio':   'xx',
    'powerline_freqs':   '50Hz, 100Hz, ...',
    'bad_count':         'xx',
    'total_channels':    'XX',
    'bad_ratio':         'xx',
    'amp_range':         '[-500,500]',
    'amp_p1_p99':        '',
    'amp_p5_p95':        '',
    'std_range':         '[-200,200]',
    'std_p1_p99':        '',
    'std_p5_p95':        '',
    'snr_range':         '[19,20]',
    'impedance_range':   '[]',
    # 电极图
    'bad_channels':      [],
    # 数据采集摘要
    'sample_rate':       '2000.0 Hz',
    'n_channels':        '128',
    'duration':          '673.34 秒',
    'data_kb':           '1,346,688.00',
    'data_mb':           '1,315.12',
    # 工频干扰（每行：[频率, 通道计数, 干扰通道描述]）
    'powerline_table': [
        ['50.0 Hz',  '127', '1, 10, 100, 101, 102, 103, 104, 105'],
        ['99.9 Hz',  '127', '1, 10, 100, 101, 102, 103, 104'],
        ['150.1 Hz', '94',  '10, 100, 101, 103, 106, 11'],
        ['199.9 Hz', '82',  '1, 10, 100, 102, 103, 104'],
        ['250.0 Hz', '37',  '106, 110, 111, 112, 113'],
        ['299.8 Hz', '125', '1, 10, 100, 101, 102, 103'],
        ['350.2 Hz', '126', '1, 10, 100, 101, 102, 103'],
        ['399.8 Hz', '125', '1, 10, 100, 101, 102, 103, 104'],
        ['450.0 Hz', '44',  '100, 103, 104, 106, 113, 115'],
        ['499.7 Hz', '117', '1, 10, 100, 101, 102, 103'],
    ],
    # 预处理参数
    'notch_freqs': '50Hz, 99.9Hz, 150.1Hz, 199.9Hz, 250Hz, 299.8Hz',
    'bandpass':    '1-200 Hz',
    'avg_ref':     '是',
    # 幅度统计
    'amp_min':           '-5064.88',
    'amp_max':           '5444.50',
    'amp_mean':          '-0.00',
    'amp_median':        '0.13',
    'amp_variability':   '28.37',
    'amp_p5_p95_range':  '-33.73 – 33.11',
    # 标准差统计
    'std_min':           '-5064.88',
    'std_max':           '5444.50',
    'std_mean':          '-0.00',
    'std_median':        '0.13',
    'std_variability':   '28.37',
    'std_p5_p95_range':  '-33.73 – 33.11',
    # SNR 统计
    'snr_min':           '20.30',
    'snr_max':           '22.23',
    'snr_mean':          '20.95',
    'snr_median':        '20.92',
    'snr_variability':   '0.51',
    'snr_p5_p95_range':  '20.41 – 22.07',
}

class PDFReportGenerator:
    def __init__(self, output_path="report.pdf"):
        from reportlab.platypus import SimpleDocTemplate
        from reportlab.lib.pagesizes import A4
        self.output_path = output_path
        self.story = []
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=18*mm,
            bottomMargin=18*mm,
        )
        self._register_fonts()
        self.styles = self._create_styles()

    # ── 字体注册 ──────────────────────────────────────────────────────────
    def _register_fonts(self):
        import os
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        def _try(name, path):
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    return True
                except Exception:
                    pass
            return False

        # 正文字体：仿宋（中文）
        self.default_font = "Helvetica"
        for name, path in [
            ("FangSong", "C:/Windows/Fonts/simfang.ttf"),
            ("SimSun",   "C:/Windows/Fonts/simsun.ttc"),
            ("SimHei",   "C:/Windows/Fonts/simhei.ttf"),
            ("FangSong", "simfang.ttf"),
            ("SimSun",   "simsun.ttf"),
        ]:
            if _try(name, path):
                self.default_font = name
                print("使用字体: " + name + " (" + path + ")")
                break

        # 标题字体：黑体（加粗）
        self.heading_font = self.default_font
        for name, path in [
            ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
            ("SimHei", "simhei.ttf"),
        ]:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                except Exception:
                    pass
                self.heading_font = name
                break

        # 英文字体：Times New Roman
        self.latin_font = self.default_font
        for name, path in [
            ("TimesNewRoman", "C:/Windows/Fonts/times.ttf"),
            ("TimesNewRoman", "times.ttf"),
        ]:
            if _try(name, path):
                self.latin_font = name
                break

    # ── 样式 ──────────────────────────────────────────────────────────────
    def _create_styles(self):
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Section', fontName=self.heading_font,
            fontSize=14, spaceBefore=12, spaceAfter=8, leading=18,
        ))
        styles.add(ParagraphStyle(
            name='Body', fontName=self.default_font,
            fontSize=11, leading=14, alignment=TA_LEFT, spaceAfter=7,
        ))
        styles.add(ParagraphStyle(
            name='Footnote', fontName=self.default_font,
            fontSize=7, textColor=colors.grey, leading=9, spaceAfter=2,
        ))
        return styles

    # ── 取值辅助：优先用 results，缺省用占位符 ───────────────────────────
    def _get(self, results, key):
        if results and key in results:
            return results[key]
        return _DEFAULTS[key]

    # ── 中英混排：非 CJK 字符用 Times New Roman，CJK 保持仿宋 ──────────
    def _mix_fonts(self, text):
        import re
        if self.latin_font == self.default_font:
            return text
        parts = re.split(r'(<[^>]+>)', str(text))
        result = []
        for part in parts:
            if part.startswith('<') and part.endswith('>'):
                result.append(part)          # 标签原样保留
            else:
                def wrap(m):
                    s = m.group()
                    return "<font name='" + self.latin_font + "'>" + s + "</font>" if s else s
                result.append(re.sub(
                    r'[^\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef\uff01-\uffee]+',
                    wrap, part
                ))
        return ''.join(result)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 第1页：结论 + 电极拓扑图 + 脚注¹~⁷
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _add_conclusion(self, r):
        g = lambda k: self._get(r, k)
        self.story.append(Paragraph("结论<font size=10><super>1</super></font>：", self.styles['Section']))
        lines = [
            "信号有效时长<font size=8><super>2</super></font>：---s（" + g('effective_ratio') + "%）；",
            "工频噪声：[" + g('powerline_freqs') + "]；",
            "坏道数/总数<font size=8><super>3</super></font>（百分比）：" + str(g('bad_count')) + "/" + str(g('total_channels')) + "（" + str(g('bad_ratio')) + "%）；",
            "幅度分布范围<font size=8><super>4</super></font>：" + g('amp_range') + "uV；1%-99%区间范围：<u>" + g('amp_p1_p99') + "uV</u>；5%-95%区间范围：<u>" + g('amp_p5_p95') + "uV</u>；",
            "标准差分布范围：" + g('std_range') + "uV；1%-99%区间范围：<u>" + g('std_p1_p99') + "uV</u>；5%-95%区间范围：<u>" + g('std_p5_p95') + "uV</u>；",
            "信噪比分布范围<font size=8><super>5</super></font>：" + g('snr_range') + "dB；",
            "阻抗分布范围<font size=8><super>6</super></font>：" + g('impedance_range') + "ohm。",
            "分析拓扑<font size=8><super>7</super></font>：",
        ]
        for line in lines:
            self.story.append(Paragraph(self._mix_fonts(line), self.styles['Body']))
        self.story.append(Spacer(1, 4*mm))

    def _add_electrode_map(self, bad_channels, image_source=None):
        """
        image_source: 外部传入的电极图，支持：
          - 文件路径字符串，如 '/path/to/electrode.png'
          - BytesIO 对象（matplotlib savefig 输出）
          - None → 内部用 bad_channels 自动生成占位图
        """
        from reportlab.platypus import Image
        from reportlab.platypus.flowables import HRFlowable

        if image_source is not None:
            buf = image_source
        else:
            import matplotlib.pyplot as plt
            from io import BytesIO
            fig, ax = plt.subplots(figsize=(5.5, 9), dpi=140)
            ax.set_aspect('equal')
            ax.axis('off')
            cols, rows = 8, 16
            for r in range(rows):
                for c in range(cols):
                    ch = r * cols + c + 1
                    is_bad = ch in bad_channels
                    ax.scatter(
                        c, rows - 1 - r,
                        s=260 if is_bad else 200,
                        c='lightgray' if is_bad else 'limegreen',
                        edgecolors='gray' if is_bad else 'darkgreen',
                        linewidth=0.8,
                    )
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=160, transparent=True)
            buf.seek(0)
            plt.close(fig)

        img = Image(buf, width=11*cm, height=12*cm, kind='proportional')
        self.story.append(img)
        self.story.append(Spacer(1, 3*mm))
        self.story.append(HRFlowable(width=6*cm, thickness=0.5, color=colors.black, hAlign='LEFT'))
        self.story.append(Spacer(1, 1*mm))

        footnotes = [
            "<super>1</super> 统计分析结论均在预处理操作之后进行计算。预处理操作包括，陷波、带通滤波、降采样、去坏道后的平均参考。",
            "<super>2</super> 将信号以 5 秒为一个窗口进行划分，无重叠，若当前窗口内坏道率>30%，则视为异常片段，并将整个片段的信号舍弃，不纳入统计分析。",
            "<super>3</super> 坏道的判断标准分为两个部分：i 当前通道的标准差大于 100；ii 当前通道的阻抗大于 1Mohm。",
            "<super>4</super> 分窗口并在舍弃坏道后进行统计；标准差的计算亦是如此分析。",
            "<super>5</super> 参考 https://doi.org/10.1016/j.celrep.2023.112467 计算 LFP 的方法。",
            "<super>6</super> 根据每次数据采集前测量的阻抗文件进行统计。",
            "<super>7</super> 绿色表示正常通道，灰色表示坏道。",
        ]
        for note in footnotes:
            self.story.append(Paragraph(
                "<font name='" + self.default_font + "' size=8 color=black>" + note + "</font>",
                self.styles['Footnote'],
            ))
            self.story.append(Spacer(1, 1*mm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 第2页：数据采集摘要 / 工频干扰 / 预处理参数 / 幅度统计
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _add_summary_table(self, r):
        g = lambda k: self._get(r, k)
        data = [
            ["项目",          "数值"],
            ["采样率",        g('sample_rate')],
            ["通道数",        str(g('n_channels'))],
            ["记录时长",      g('duration')],
            ["数据大小 (KB)", g('data_kb')],
            ["数据大小 (MB)", g('data_mb')],
        ]
        self._add_table("数据采集摘要：", data, [6*cm, 10*cm])

    def _add_powerline_table(self, r):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        rows = self._get(r, 'powerline_table')
        data = [["频率", "通道计数", "干扰通道"]] + [list(row) for row in rows]
        self.story.append(Paragraph("工频干扰：", self.styles['Section']))
        hdr = ParagraphStyle('_pw_h', fontName=self.default_font,
                             fontSize=9, leading=12, alignment=TA_LEFT)
        left = ParagraphStyle('_pw_l', fontName=self.default_font,
                              fontSize=8, leading=10, alignment=TA_LEFT)
        styled_data = []
        for i, row in enumerate(data):
            if i == 0:
                styled_data.append([Paragraph(self._mix_fonts(str(c)), hdr) for c in row])
            else:
                styled_data.append([
                    Paragraph(self._mix_fonts(str(row[0])), left),
                    Paragraph(self._mix_fonts(str(row[1])), left),
                    Paragraph(self._mix_fonts(str(row[2])), left),
                ])
        table = Table(styled_data, colWidths=[4.5*cm, 4*cm, 7.5*cm])
        table.setStyle(TableStyle([
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 6*mm))

    def _add_preprocessing_table(self, r):
        g = lambda k: self._get(r, k)
        data = [
            ["项目",    "内容"],
            ["陷波频率", g('notch_freqs')],
            ["带通滤波", g('bandpass')],
            ["平均参考", g('avg_ref')],
        ]
        self._add_table("预处理参数：", data, [5.5*cm, 10.5*cm])

    def _add_amp_table(self, r):
        g = lambda k: self._get(r, k)
        data = [
            ["统计量",  "数值 (μV)"],
            ["最小值",  g('amp_min')],
            ["最大值",  g('amp_max')],
            ["均值",    g('amp_mean')],
            ["中位数",  g('amp_median')],
            ["变异性",  g('amp_variability')],
            ["5%-95%", g('amp_p5_p95_range')],
        ]
        self._add_table("幅度统计：", data, [8*cm, 8*cm])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 第3页：标准差统计 / SNR统计 / 趋势图1 + 脚注⁸
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _add_std_table(self, r):
        g = lambda k: self._get(r, k)
        data = [
            ["统计量",  "数值 (μV)"],
            ["最小值",  g('std_min')],
            ["最大值",  g('std_max')],
            ["均值",    g('std_mean')],
            ["中位数",  g('std_median')],
            ["变异性",  g('std_variability')],
            ["5%-95%", g('std_p5_p95_range')],
        ]
        self._add_table("标准差统计：", data, [8*cm, 8*cm])

    def _add_snr_table(self, r):
        g = lambda k: self._get(r, k)
        data = [
            ["统计量",  "数值 (dB)"],
            ["最小值",  g('snr_min')],
            ["最大值",  g('snr_max')],
            ["均值",    g('snr_mean')],
            ["中位数",  g('snr_median')],
            ["变异性",  g('snr_variability')],
            ["5%-95%", g('snr_p5_p95_range')],
        ]
        self._add_table("SNR 统计：", data, [8*cm, 8*cm])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 趋势图（占位随机波形，接口数据传入时替换）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _make_trend_elements(self, title, image_source=None, n_channels=128, duration_min=11.22):
        """
        生成趋势图 flowable 列表（不直接写入 story）。
        image_source: 外部传入的趋势图，支持文件路径字符串或 BytesIO；
                      为 None 时内部生成随机占位波形。
        """
        from reportlab.platypus import Image

        if image_source is not None:
            buf = image_source
        else:
            import numpy as np
            import matplotlib.pyplot as plt
            from io import BytesIO
            fig, ax = plt.subplots(figsize=(14, 7.5), dpi=130)
            t = np.linspace(0, duration_min, 300)
            for i in range(n_channels):
                y = np.sin(t * 2 * np.pi * 0.3 + i) * 3 + np.random.randn(len(t)) * 1.5
                ax.plot(t, y + i * 6, lw=0.6, color='navy', alpha=0.7)
            ax.set_xlabel("t/min")
            ax.set_ylabel("ch")
            ax.grid(True, alpha=0.25, linestyle='--')
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)
            plt.close(fig)

        return [
            Paragraph(title + "：", self.styles['Section']),
            Image(buf, width=17*cm, height=10*cm),
            Spacer(1, 6*mm),
        ]

    def add_trend_plot(self, title, image_source=None, n_channels=128, duration_min=11.22):
        """公开接口：趋势图直接追加到 story（用于趋势图2）"""
        self.story.extend(self._make_trend_elements(title, image_source, n_channels, duration_min))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 通用表格
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _add_table(self, title, data, col_widths):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        self.story.append(Paragraph(title, self.styles['Section']))
        hdr_style = ParagraphStyle('_th', fontName=self.default_font,
                                   fontSize=9, leading=12, alignment=TA_LEFT)
        row_style = ParagraphStyle('_td', fontName=self.default_font,
                                   fontSize=8.5, leading=11, alignment=TA_LEFT)
        styled_data = [
            [Paragraph(self._mix_fonts(str(cell)), hdr_style if i == 0 else row_style)
             for cell in row]
            for i, row in enumerate(data)
        ]
        table = Table(styled_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 5*mm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 主入口
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def build_report(self, results=None):

        from reportlab.platypus import PageBreak, KeepTogether
        from reportlab.platypus.flowables import HRFlowable

        r = results or {}
        bad_ch = set(r.get('bad_channels', _DEFAULTS['bad_channels']))

        # ── 第1页 ────────────────────────────────────────────
        self._add_conclusion(r)
        self._add_electrode_map(bad_ch, image_source=r.get('electrode_map_image'))
        self.story.append(PageBreak())

        # ── 第2页 ────────────────────────────────────────────
        self._add_summary_table(r)
        self._add_powerline_table(r)
        self._add_preprocessing_table(r)
        self._add_amp_table(r)

        # ── 第3页 ────────────────────────────────────────────
        self._add_std_table(r)
        self._add_snr_table(r)

        footnote8 = Paragraph(
            "<font name='" + self.default_font + "' size=8 color=black>"
            "<super>8</super> 对信号做预处理后，以 5 秒为一个窗口计算均值，并观察有效通道的变化趋势。"
            "</font>",
            self.styles['Footnote'],
        )
        self.story.append(KeepTogether(
            self._make_trend_elements(
                "信号变化趋势 1（均值）<font size=10><super>8</super></font>",
                image_source=r.get('trend1_image'),
            ) + [
                Spacer(1, 3*mm),
                HRFlowable(width=6*cm, thickness=0.5, color=colors.black, hAlign='LEFT'),
                Spacer(1, 1*mm),
                footnote8,
            ]
        ))
        self.story.append(PageBreak())

        # ── 第4页 ────────────────────────────────────────────
        self.add_trend_plot("信号变化趋势 2（标准差）", image_source=r.get('trend2_image'))

        self.doc.build(self.story)
        print("报告已生成：" + self.output_path)

if __name__ == "__main__":
    # ── 测试：用占位符生成 ────────────────────────────────────
    gen = PDFReportGenerator("质量分析报告.pdf")
    gen.build_report()
    
