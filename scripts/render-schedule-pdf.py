#!/usr/bin/env python3
"""Render the printable timetable from the website data (Node, ReportLab, Fontconfig)."""
import json
from pathlib import Path
import subprocess

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
data = json.loads(subprocess.check_output([
    'node', '--input-type=module', '-e',
    "import * as data from './schedule-data.js'; console.log(JSON.stringify(data));",
], cwd=ROOT, text=True))
font_path = subprocess.check_output([
    'fc-match', '-f', '%{file}', 'Liberation Sans:style=Bold',
], text=True).strip()
pdfmetrics.registerFont(TTFont('Schedule', font_path))

output = ROOT / 'schedule.pdf'
width, height = landscape(A4)
margin = 36
table_width = width - 2 * margin
document = canvas.Canvas(str(output), pagesize=(width, height), invariant=1, pageCompression=1)
document.setTitle('Расписание уроков · ' + data['SCHOOL'])
document.setAuthor(data['SCHOOL'])
document.setFont('Schedule', 17)
document.drawCentredString(width / 2, height - 50, 'РАСПИСАНИЕ УРОКОВ')
document.setFont('Schedule', 10)
document.drawCentredString(width / 2, height - 64, data['SCHOOL'])
document.setLineWidth(1.4)
document.line(margin, height - 73, width - margin, height - 73)

rows = [['№', 'ВРЕМЯ УРОКА', *[day.upper() for day in data['WEEKDAYS']]]]
for index, (start, end) in enumerate(data['BELL_TIMES']):
    rows.append([str(index + 1), f'{start} – {end}', *[
        (f"{lessons[index]}\nкаб. {data['ROOMS'][day][index]}"
         if data['ROOMS'][day][index] else lessons[index] or '—')
        for day, lessons in enumerate(data['LESSONS'])
    ]])

table = Table(rows, colWidths=[table_width * share for share in [0.05, 0.16, *[0.158] * 5]],
              rowHeights=[25.2, *[32] * len(data['BELL_TIMES'])])
table.setStyle(TableStyle([
    ('FONTNAME', (0, 0), (-1, -1), 'Schedule'),
    ('FONTSIZE', (0, 0), (-1, -1), 9.75),
    ('FONTSIZE', (1, 1), (1, -1), 9),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 0),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f2f2f2')),
    ('BACKGROUND', (1, 1), (1, -1), colors.HexColor('#fafafa')),
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e5e5')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ('BOX', (0, 0), (-1, -1), 1.4, colors.black),
    ('LINEBELOW', (0, 0), (-1, 0), 1.4, colors.black),
]))
_, table_height = table.wrap(table_width, height)
table_bottom = height - 82 - table_height
table.drawOn(document, margin, table_bottom)


def minutes(time):
    hours, minute = map(int, time.split(':'))
    return hours * 60 + minute


bells = data['BELL_TIMES']
breaks = [str(minutes(bells[index + 1][0]) - minutes(end))
          for index, (_, end) in enumerate(bells[:-1])]
footer_bottom = table_bottom - 30
document.setLineWidth(0.8)
document.rect(margin, footer_bottom, table_width, 21)
document.setFont('Schedule', 8)
document.drawString(margin + 9, footer_bottom + 7,
                    'ПЕРЕМЕНЫ ПОСЛЕ УРОКОВ: ' + ' / '.join(breaks) + ' мин')
duration = minutes(bells[0][1]) - minutes(bells[0][0])
document.drawRightString(width - margin - 9, footer_bottom + 7,
                         f'Урок: {duration} МИН | Начало занятий: {bells[0][0]}')
document.showPage()
document.save()
print(f'Generated {output}: {output.stat().st_size} bytes')
