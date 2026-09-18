# v116 school schedule

The standalone static website for [v116.spb.ru](https://v116.spb.ru/), the
Russian-language schedule for гимназия № 116, class 5В.

The browser performs all rendering and Moscow-time calculations. There are no
runtime dependencies, external fonts, analytics, backend, or JavaScript build
step. The files in this repository can be served directly by any static web
server.

## Development

```bash
node tests/schedule.test.mjs
python3 scripts/render-schedule-pdf.py
python3 -m http.server 8765 --bind 127.0.0.1
python3 tests/schedule-browser.py
```

The PDF generator requires Node.js, Python ReportLab, Fontconfig, and
Liberation Sans. The optional browser checks require Python Playwright and
Google Chrome.

Edit `schedule-data.js` when the timetable changes, regenerate `schedule.pdf`,
and keep the download size in `index.html` current if the file size changes.

