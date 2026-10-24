# v116 school schedule

The standalone static website for [v116.spb.ru](https://v116.spb.ru/), the
Russian-language schedule for gymnasium № 116, class 5В.

The browser performs all rendering and Moscow-time calculations. 
There are no runtime dependencies, external fonts, analytics, backend, 
or JavaScript build step. 

The files in this repository can be served directly by any static web server.

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

Edit `holiday-data.js` for official holiday dates (inclusive, specific to the school
year). Holiday mode includes immediately adjacent Saturdays and Sundays, while
messages and the expandable holiday calendar retain the official dates and lengths.
During holidays, the first school day after the break is selected by default.
The current holiday notice and seasonal decorations stay visible while browsing
any date. Selecting a holiday weekday shows its usual timetable as a reference,
clearly marked as a day without classes, with no live lesson tracking.
All date boundaries follow Moscow time, including when the page stays open overnight.
Seasonal decorations are disabled for reduced-motion preferences.

`public-holiday-data.js` contains Russia's federal non-working holidays and
transferred days off for **2026**. The next study day skips these dates as well as
weekends and school holidays. Their usual timetables remain available as a reference,
without live tracking. Shortened working days and commemorative dates are not days off.
This calendar is bundled locally; there is no runtime API dependency. Add each new
year explicitly after checking its official dates and transfers.

Sources: [Bank of Russia, 2026 calendar](https://www.cbr.ru/other/holidays/) and
[Government decree No. 1466 of 24 September 2025](https://publication.pravo.gov.ru/document/0001202509240023).
