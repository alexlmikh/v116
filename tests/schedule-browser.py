"""Browser checks: pip install playwright; uses installed Google Chrome.

Start `python3 -m http.server 8765` first, then run
`python3 tests/schedule-browser.py [URL]`. Screenshots go to /tmp.
"""
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import hashlib
import re
import shutil
import sys

from playwright.sync_api import sync_playwright, expect

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/'
PDF = Path(__file__).resolve().parents[1] / 'schedule.pdf'


def instant(value):
    return datetime.fromisoformat(value)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=shutil.which('google-chrome'), headless=True)
    context = browser.new_context(viewport={'width': 390, 'height': 844},
                                  is_mobile=True, has_touch=True, timezone_id='Pacific/Honolulu')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.clock.install(time=instant('2026-09-11T08:45:00+03:00'))
    page.clock.pause_at(instant('2026-09-11T08:45:00+03:00'))
    page.goto(URL)
    expect(page.locator('#preview-notice')).to_be_hidden()
    expect(page.locator('#day-name')).to_have_text('Пятница')
    expect(page.locator('#clock')).to_have_text('08:45')
    expect(page.locator('.is-current h3')).to_have_text('Английский язык')
    expect(page.locator('#status-detail')).to_have_text('До конца 30 мин · Английский язык')
    expect(page.locator('#status-room .lesson-room')).to_have_text('103 / 320')
    expect(page.locator('#status-room .lesson-room')).to_have_accessible_name('Кабинеты 103 и 320')
    expect(page.locator('.is-current .lesson-time')).to_have_text('08:30 — 09:15')
    expect(page.locator('.is-current .lesson-room')).to_have_text('103 / 320')
    expect(page.locator('.is-current .lesson-room')).to_have_accessible_name('Кабинеты 103 и 320')
    assert page.locator('.lesson-room[title]').count() == 0
    # Room badges stay centered on the subject, even when "Сейчас" wraps below it.
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 844})
        assert page.locator('.lesson .lesson-room').evaluate_all('''rooms => rooms.every(room => {
            const lesson = room.closest('.lesson');
            const subject = lesson.querySelector('h3').getBoundingClientRect();
            const badge = room.getBoundingClientRect();
            const time = lesson.querySelector('.lesson-time').getBoundingClientRect();
            return Math.abs((subject.top + subject.bottom - badge.top - badge.bottom) / 2) < 1
                && badge.left >= subject.right && time.top >= Math.max(subject.bottom, badge.bottom);
        })'''), f'Room badge not aligned with subject at {width}px'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path='/tmp/v116-schedule-mobile.png', full_page=True)

    # Hints are absent until interaction, including on phones without hover.
    room = page.locator('.is-current .lesson-room')
    hint = page.locator('.is-current .room-tooltip')
    expect(hint).to_be_hidden()
    room.tap()
    expect(hint).to_be_visible()
    expect(hint).to_have_text('Кабинеты 103 и 320')
    room.tap()
    expect(hint).to_be_hidden()
    room.tap()
    page.locator('h1').tap()
    expect(hint).to_be_hidden()

    # Keyboard focus opens a hint; Escape dismisses it without moving focus.
    page.locator('#next').focus()
    for _ in range(6):
        page.keyboard.press('Tab')
    expect(page.locator('#status-room .lesson-room')).to_be_focused()
    expect(page.locator('#room-tooltip-status')).to_be_visible()
    page.keyboard.press('Tab')
    expect(room).to_be_focused()
    expect(hint).to_be_visible()
    page.keyboard.press('Escape')
    expect(hint).to_be_hidden()
    expect(room).to_be_focused()
    page.keyboard.press('Tab')
    expect(page.locator('[role="tooltip"]:visible')).to_have_text('Кабинет 325')

    # Navigation must never mark a lesson on another date as happening now.
    page.locator('#next').click()
    expect(page.locator('#day-name')).to_have_text('Понедельник')
    expect(page.locator('#full-date')).to_have_text('14 сентября 2026 г.')
    expect(page.locator('.is-current')).to_have_count(0)
    expect(page.locator('#status-room')).to_be_hidden()
    page.get_by_role('button', name='Среда, 16 сентября 2026 г.').click()
    expect(page.locator('.lesson')).to_have_count(6)
    expect(page.locator('#end-of-day')).to_have_text('Конец занятий в 14:20')
    page.locator('#today').click()
    expect(page.locator('#day-name')).to_have_text('Пятница')
    page.locator('#previous').click()
    expect(page.locator('#day-name')).to_have_text('Четверг')
    page.locator('#today').click()

    # Boundary updates happen without a reload; next lesson/break states replace one another.
    page.clock.fast_forward((29 * 60 + 59) * 1000)
    expect(page.locator('.is-current h3')).to_have_text('Английский язык')
    expect(page.locator('.is-current-break')).to_have_count(0)
    page.clock.fast_forward(1000)
    expect(page.locator('.is-current')).to_have_count(0)
    expect(page.locator('#status-title')).to_have_text('Перемена · ещё 10 мин')
    expect(page.locator('#status-detail')).to_have_text('Далее: Литература в 09:25')
    expect(page.locator('#status-room .lesson-room')).to_have_text('325')
    expect(page.locator('.is-current-break')).to_have_count(1)
    expect(page.locator('.lesson[data-number="1"] .break-label')).to_have_attribute('aria-current', 'true')
    expect(page.locator('.is-current-break')).to_have_css('color', 'rgb(33, 104, 89)')
    expect(page.locator('.is-current-break')).to_have_css('font-weight', '650')
    expect(page.locator('.break-label:not(.is-current-break)').first).to_have_css('color', 'rgb(100, 112, 121)')
    expect(page.locator('.break-label:not(.is-current-break)').first).to_have_css('font-weight', '400')
    page.screenshot(path='/tmp/v116-schedule-break.png', full_page=True)
    page.locator('#next').click()
    expect(page.locator('.is-current-break')).to_have_count(0)
    page.locator('#today').click()
    expect(page.locator('.is-current-break')).to_have_count(1)
    page.clock.fast_forward((9 * 60 + 59) * 1000)
    expect(page.locator('.is-current-break')).to_have_count(1)
    page.clock.fast_forward(1000)
    expect(page.locator('.is-current h3')).to_have_text('Литература')
    expect(page.locator('.is-current-break')).to_have_count(0)
    expect(page.locator('.lesson[data-number="1"] .break-label')).to_have_css('color', 'rgb(100, 112, 121)')
    expect(page.locator('.lesson[data-number="1"] .break-label')).to_have_css('font-weight', '400')
    expect(page.locator('.is-current .lesson-room')).to_have_text('325')
    expect(page.locator('#status-room .lesson-room')).to_have_text('325')
    page.clock.fast_forward((4 * 60 + 55) * 60 * 1000)
    expect(page.locator('#status-title')).to_have_text('На сегодня всё!')
    expect(page.locator('.is-current-break')).to_have_count(0)
    expect(page.locator('#status-room')).to_be_hidden()

    # Moscow Saturday begins while the emulated phone is still on Friday.
    page.clock.fast_forward((9 * 60 + 40) * 60 * 1000)
    expect(page.locator('#day-name')).to_have_text('Понедельник')
    expect(page.locator('#weekend-notice')).to_contain_text('Сегодня выходной')
    expect(page.locator('#weekend-notice')).to_contain_text('14 сентября')
    expect(page.locator('.is-current-break')).to_have_count(0)
    expect(page.locator('.is-current')).to_have_count(0)
    page.screenshot(path='/tmp/v116-schedule-weekend.png', full_page=True)
    page.clock.fast_forward(24 * 60 * 60 * 1000)
    expect(page.locator('#full-date')).to_have_text('14 сентября 2026 г.')
    expect(page.locator('#weekend-notice')).to_be_visible()
    page.clock.fast_forward(24 * 60 * 60 * 1000)
    expect(page.locator('#weekend-notice')).to_be_hidden()
    expect(page.locator('#relative-day')).to_have_text('Сегодня')
    expect(page.locator('#status-title')).to_have_text('Первый урок в 08:30')
    expect(page.locator('#status-room')).to_be_hidden()  # Monday's first lesson has no room.

    # Pinning another day survives midnight, and Today resumes following the clock.
    page.locator('#next').click()
    page.clock.fast_forward(3 * 24 * 60 * 60 * 1000)
    expect(page.locator('#day-name')).to_have_text('Вторник')
    page.locator('#today').click()
    expect(page.locator('#day-name')).to_have_text('Четверг')

    for width in (320, 375, 390, 768, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
        assert page.locator('.lesson-room').evaluate_all('''rooms => rooms.every(room => {
            const icon = room.querySelector('svg').getBoundingClientRect();
            const number = room.querySelector('.room-number').getBoundingClientRect();
            return Math.abs((icon.top + icon.bottom - number.top - number.bottom) / 2) < 1;
        })'''), f'Room icon misaligned at {width}px'
    page.screenshot(path='/tmp/v116-schedule-desktop.png', full_page=True)

    with page.expect_download() as download_event:
        page.locator('.pdf-card').click()
    download = download_event.value
    assert download.suggested_filename == 'Расписание-5В.pdf'
    assert hashlib.sha256(Path(download.path()).read_bytes()).digest() == hashlib.sha256(PDF.read_bytes()).digest()

    # Wednesday's added sixth lesson must remain active until 14:20.
    page.clock.set_fixed_time(instant('2026-09-16T13:35:00+03:00'))
    page.goto(URL)
    expect(page.locator('#day-name')).to_have_text('Среда')
    expect(page.locator('.is-current h3')).to_have_text('География')
    expect(page.locator('#end-of-day')).to_have_text('Конец занятий в 14:20')
    page.screenshot(path='/tmp/v116-schedule-wednesday.png', full_page=True)
    # Before lessons, show the first room; during PE, clear the preceding room.
    page.clock.set_fixed_time(instant('2026-09-15T08:00:00+03:00'))
    page.goto(URL)
    expect(page.locator('#status-room .lesson-room')).to_have_text('325')
    expect(page.locator('.is-current-break')).to_have_count(0)
    page.locator('#status-room .lesson-room').tap()
    expect(page.locator('#room-tooltip-status')).to_be_visible()
    page.locator('h1').tap()
    expect(page.locator('#room-tooltip-status')).to_be_hidden()
    page.clock.set_fixed_time(instant('2026-09-15T11:30:00+03:00'))
    page.goto(URL)
    expect(page.locator('#status-title')).to_contain_text('Перемена')
    expect(page.locator('.is-current-break')).to_have_count(1)
    expect(page.locator('.lesson[data-number="3"] .break-label')).to_have_attribute('aria-current', 'true')
    expect(page.locator('#status-room')).to_be_hidden()
    page.clock.set_fixed_time(instant('2026-09-15T11:40:00+03:00'))
    page.reload()
    expect(page.locator('#status-title')).to_have_text('Идёт 4-й урок')
    expect(page.locator('#status-room')).to_be_hidden()

    # The opt-in preview freezes a break even after school or on a weekend.
    for actual_date, preview_date in (('2026-09-11', '2026-09-11'), ('2026-09-12', '2026-09-14')):
        page.clock.set_fixed_time(instant(f'{actual_date}T20:00:00+03:00'))
        page.goto(urljoin(URL, '?previewBreak'))
        expect(page.locator('#preview-notice')).to_be_visible()
        expect(page.locator('#clock')).to_have_text('09:20')
        expect(page.locator('#clock')).to_have_attribute('datetime', f'{preview_date}T09:20:00+03:00')
        expect(page.locator('#status-title')).to_have_text('Перемена · ещё 5 мин')
        expect(page.locator('.is-current')).to_have_count(0)
        expect(page.locator('.is-current-break')).to_have_count(1)
        expect(page.locator('.lesson[data-number="1"] .break-label')).to_have_attribute('aria-current', 'true')
        page.clock.fast_forward(10 * 60 * 1000)
        expect(page.locator('#clock')).to_have_text('09:20')
        expect(page.locator('#status-title')).to_have_text('Перемена · ещё 5 мин')
        page.locator('#next').click()
        expect(page.locator('.is-current-break')).to_have_count(0)
        page.locator('#today').click()
        expect(page.locator('.is-current-break')).to_have_count(1)
        page.screenshot(path='/tmp/v116-schedule-preview-break.png', full_page=True)
        page.goto(URL)
        expect(page.locator('#preview-notice')).to_be_hidden()
        expect(page.locator('#clock')).to_have_text('20:00')
        expect(page.locator('.is-current-break')).to_have_count(0)
    # Holidays keep their notice and effects while showing the first day after the break.
    holiday_cases = (
        ('2026-10-24', 'autumn', 'Осенние', '26 октября – 3 ноября 2026 · 9 дней'),
        ('2026-10-25', 'autumn', 'Осенние', '26 октября – 3 ноября 2026 · 9 дней'),
        ('2026-10-26', 'autumn', 'Осенние', '26 октября – 3 ноября 2026 · 9 дней'),
        ('2026-11-03', 'autumn', 'Осенние', '26 октября – 3 ноября 2026 · 9 дней'),
        ('2026-12-31', 'winter', 'Зимние', '31 декабря 2026 – 10 января 2027 · 11 дней'),
        ('2027-01-10', 'winter', 'Зимние', '31 декабря 2026 – 10 января 2027 · 11 дней'),
        ('2027-03-27', 'spring', 'Весенние', '27 марта – 4 апреля 2027 · 9 дней'),
        ('2027-04-04', 'spring', 'Весенние', '27 марта – 4 апреля 2027 · 9 дней'),
        ('2027-05-27', 'summer', 'Летние', '27 мая – 31 августа 2027 · 97 дней'),
        ('2027-08-31', 'summer', 'Летние', '27 мая – 31 августа 2027 · 97 дней'),
    )
    for date, season, name, dates in holiday_cases:
        page.clock.set_fixed_time(instant(f'{date}T08:45:00+03:00'))
        page.goto(URL)
        first_day = {'autumn': '5 ноября 2026 г.', 'winter': '11 января 2027 г.',
                     'spring': '5 апреля 2027 г.', 'summer': '1 сентября 2027 г.'}[season]
        expect(page.locator('#holiday-title')).to_have_text(f'{name} каникулы')
        expect(page.locator('#holiday-detail')).to_contain_text(dates)
        expect(page.locator('#status-title')).to_have_text('План на день')
        expect(page.locator('#full-date')).to_have_text(first_day)
        expect(page.locator('#relative-day')).to_have_text('После каникул')
        expect(page.locator('#weekend-notice')).to_be_hidden()
        expect(page.locator('#status-room')).to_be_hidden()
        expect(page.locator('#lessons')).to_be_visible()
        expect(page.locator('.lesson')).to_have_count(6)
        expect(page.locator('.is-current, .is-current-break, .is-past')).to_have_count(0)
        expect(page.locator('.end-of-day')).to_be_visible()
        expect(page.locator('#holiday-effects')).to_have_attribute('data-season', season)
        expect(page.locator('.season-particle')).to_have_count(12)
        expect(page.locator('#holiday-effects')).to_have_attribute('aria-hidden', 'true')
        assert page.locator('#holiday-effects').evaluate('el => getComputedStyle(el).pointerEvents') == 'none'
        page.locator('#holiday-schedule summary').click()
        expect(page.locator('#holiday-list li')).to_have_count(4)
        expect(page.locator('#holiday-list')).to_contain_text(dates)
        for width in (320, 390, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Holiday overflow: {season}, {width}px'
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=f'/tmp/v116-holiday-{season}.png', full_page=True)
        # Neither arrows nor weekday buttons reset the effects or remove the notice.
        page.evaluate('window.firstParticle = document.querySelector(".season-particle")')
        page.locator('#next').click()
        page.locator('#week button').last.click()
        expect(page.locator('#holiday-notice')).to_be_visible()
        expect(page.locator('#holiday-title')).to_have_text(f'{name} каникулы')
        expect(page.locator('#holiday-detail')).to_contain_text(dates)
        expect(page.locator('#holiday-effects')).to_have_attribute('data-season', season)
        assert page.evaluate('window.firstParticle === document.querySelector(".season-particle")')
        expect(page.locator('#today')).to_have_text('К первому дню после каникул')
        page.locator('#today').click()
        expect(page.locator('#full-date')).to_have_text(first_day)

    # A holiday weekday still offers the usual timetable, with no live tracking.
    page.clock.set_fixed_time(instant('2027-08-31T12:00:00+03:00'))
    page.reload()
    page.locator('#previous').click()
    expect(page.locator('#full-date')).to_have_text('31 августа 2027 г.')
    expect(page.locator('#status-title')).to_have_text('Обычное расписание')
    expect(page.locator('#status-detail')).to_contain_text('В этот день занятий нет')
    expect(page.locator('.lesson')).to_have_count(6)
    expect(page.locator('.is-current, .is-current-break, .is-past')).to_have_count(0)
    expect(page.locator('#holiday-notice')).to_be_visible()
    expect(page.locator('#holiday-effects')).to_be_visible()
    page.locator('#today').click()
    expect(page.locator('#full-date')).to_have_text('1 сентября 2027 г.')
    expect(page.locator('#holiday-title')).to_have_text('Летние каникулы')
    expect(page.locator('.season-particle').first).to_have_css('animation-play-state', 'running')
    page.emulate_media(reduced_motion='reduce')
    expect(page.locator('#holiday-effects')).to_be_hidden()
    expect(page.locator('.season-particle').first).to_have_css('animation-name', 'none')
    page.emulate_media(reduced_motion='no-preference')

    # Browsing a future holiday on a teaching day does not change today's atmosphere.
    page.clock.set_fixed_time(instant('2026-10-23T08:45:00+03:00'))
    page.goto(URL)
    page.locator('#next').click()
    expect(page.locator('#status-title')).to_have_text('Обычное расписание')
    expect(page.locator('#holiday-notice')).to_be_hidden()
    expect(page.locator('#holiday-effects')).to_be_hidden()
    expect(page.locator('.lesson')).to_have_count(6)

    # Federal holidays and transferred days off keep their notice while browsing.
    for date, name, next_date in (
        ('2026-01-09', 'Перенесённый выходной за 3 января', '12 января 2026 г.'),
        ('2026-02-23', 'День защитника Отечества', '24 февраля 2026 г.'),
        ('2026-03-09', 'Перенесённый выходной за 8 марта', '10 марта 2026 г.'),
        ('2026-05-01', 'Праздник Весны и Труда', '4 мая 2026 г.'),
        ('2026-05-11', 'Перенесённый выходной за 9 мая', '12 мая 2026 г.'),
        ('2026-06-12', 'День России', '15 июня 2026 г.'),
        ('2026-11-04', 'День народного единства', '5 ноября 2026 г.'),
    ):
        page.clock.set_fixed_time(instant(f'{date}T12:00:00+03:00'))
        page.goto(URL)
        expect(page.locator('#holiday-title')).to_have_text(name)
        expect(page.locator('#holiday-notice')).to_be_visible()
        expect(page.locator('#holiday-effects')).to_be_hidden()
        expect(page.locator('#full-date')).to_have_text(next_date)
        expect(page.locator('#relative-day')).to_have_text('Ближайший')
        expect(page.locator('#status-title')).to_have_text('План на день')
        page.locator('#previous').click()
        expect(page.locator(f'#week button[data-date="{date}"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#status-title')).to_have_text('Обычное расписание')
        expect(page.locator('#status-detail')).to_have_text(f'{name}. В этот день занятий нет.')
        expect(page.locator('#status-room')).to_be_hidden()
        expect(page.locator('.end-of-day')).to_be_hidden()
        expect(page.locator('.lesson')).to_have_count(6)
        expect(page.locator('.is-current, .is-current-break, .is-past')).to_have_count(0)
        expect(page.locator('#holiday-title')).to_have_text(name)
        expect(page.locator('#today')).to_have_text('К ближайшему учебному дню')
        page.locator('#today').click()
        expect(page.locator('#full-date')).to_have_text(next_date)
    page.screenshot(path='/tmp/v116-unity-day.png', full_page=True)

    # A long weekend can resume on Tuesday; the notice must not promise Monday.
    page.clock.set_fixed_time(instant('2026-03-07T12:00:00+03:00'))
    page.goto(URL)
    expect(page.locator('#full-date')).to_have_text('10 марта 2026 г.')
    expect(page.locator('#weekend-notice')).to_have_text('Сегодня выходной. Показываем ближайший учебный день, 10 марта 2026 г.')

    # The existing explicit break preview still works during a holiday.
    page.clock.set_fixed_time(instant('2026-10-24T20:00:00+03:00'))
    page.goto(urljoin(URL, '?previewBreak'))
    expect(page.locator('#status-title')).to_have_text('Перемена · ещё 5 мин')
    expect(page.locator('#full-date')).to_have_text('5 ноября 2026 г.')
    expect(page.locator('#holiday-effects')).to_be_hidden()

    # Cross holiday boundaries at Moscow midnight without reloading the page.
    transitions = context.new_page()
    transitions.on('pageerror', lambda error: errors.append(str(error)))
    transitions.clock.install(time=instant('2026-10-23T23:59:59+03:00'))
    transitions.clock.pause_at(instant('2026-10-23T23:59:59+03:00'))
    transitions.goto(URL)
    expect(transitions.locator('#status-title')).to_have_text('На сегодня всё!')
    transitions.clock.fast_forward(1000)
    expect(transitions.locator('#full-date')).to_have_text('5 ноября 2026 г.')
    expect(transitions.locator('#holiday-title')).to_have_text('Осенние каникулы')
    expect(transitions.locator('#status-title')).to_have_text('План на день')
    expect(transitions.locator('.lesson')).to_have_count(6)
    transitions.clock.fast_forward(24 * 60 * 60 * 1000)
    expect(transitions.locator('#full-date')).to_have_text('5 ноября 2026 г.')
    expect(transitions.locator('#holiday-title')).to_have_text('Осенние каникулы')
    transitions.clock.fast_forward(10 * 24 * 60 * 60 * 1000)
    expect(transitions.locator('#full-date')).to_have_text('5 ноября 2026 г.')
    expect(transitions.locator('#status-title')).to_have_text('План на день')
    expect(transitions.locator('#holiday-title')).to_have_text('День народного единства')
    expect(transitions.locator('#holiday-effects')).to_be_hidden()
    transitions.clock.fast_forward(24 * 60 * 60 * 1000)
    expect(transitions.locator('#status-title')).to_have_text('Первый урок в 08:30')
    expect(transitions.locator('#holiday-notice')).to_be_hidden()
    expect(transitions.locator('#holiday-effects')).to_be_hidden()
    transitions.clock.fast_forward((8 * 60 + 45) * 60 * 1000)
    expect(transitions.locator('.is-current h3')).to_have_text('Русский язык')
    transitions.close()

    # A pinned date survives the school break -> Unity Day -> teaching day transitions.
    pinned = context.new_page()
    pinned.on('pageerror', lambda error: errors.append(str(error)))
    pinned.clock.install(time=instant('2026-11-03T23:59:59+03:00'))
    pinned.clock.pause_at(instant('2026-11-03T23:59:59+03:00'))
    pinned.goto(URL)
    pinned.locator('#week button[data-date="2026-11-03"]').click()
    expect(pinned.locator('#full-date')).to_have_text('3 ноября 2026 г.')
    expect(pinned.locator('#holiday-notice')).to_be_visible()
    pinned.clock.fast_forward(1000)
    expect(pinned.locator('#full-date')).to_have_text('3 ноября 2026 г.')
    expect(pinned.locator('#holiday-title')).to_have_text('День народного единства')
    pinned.clock.fast_forward(24 * 60 * 60 * 1000)
    expect(pinned.locator('#holiday-notice')).to_be_hidden()
    expect(pinned.locator('#holiday-effects')).to_be_hidden()
    expect(pinned.locator('#status-title')).to_have_text('Обычное расписание')
    pinned.locator('#today').click()
    expect(pinned.locator('#full-date')).to_have_text('5 ноября 2026 г.')
    pinned.close()
    assert not errors, errors
    context.close()

    desktop = browser.new_context(viewport={'width': 390, 'height': 844})
    page = desktop.new_page()
    page.clock.set_fixed_time(instant('2026-09-11T08:45:00+03:00'))
    page.goto(URL)
    room = page.locator('.lesson-room').first
    hint = page.locator('.room-tooltip').first
    for width in (320, 390, 1440):
        page.set_viewport_size({'width': width, 'height': 900})
        room.hover()
        expect(hint).to_be_visible()
        bounds = hint.bounding_box()
        assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= width
        hint.hover()
        expect(hint).to_be_visible()
        page.keyboard.press('Escape')
        expect(hint).to_be_hidden()
        page.locator('h1').hover()
        room.hover()
        expect(hint).to_be_visible()
        page.locator('h1').hover()
        expect(hint).to_be_hidden()
    desktop.close()

    # A returning visitor may still have an older unversioned module cached.
    cached = browser.new_context(viewport={'width': 390, 'height': 844})
    stale_time_module = (PDF.parent / 'schedule-time.js').read_text().replace(
        'export function holidayDates', 'function holidayDates')
    cached.route(re.compile(r'/schedule-time\.js$'), lambda route: route.fulfill(
        content_type='text/javascript', body=stale_time_module))
    page = cached.new_page()
    cache_errors = []
    page.on('pageerror', lambda error: cache_errors.append(str(error)))
    page.clock.set_fixed_time(instant('2026-10-24T08:45:00+03:00'))
    page.goto(URL)
    expect(page.locator('#schedule')).to_be_visible()
    expect(page.locator('#holiday-title')).to_have_text('Осенние каникулы')
    expect(page.locator('#full-date')).to_have_text('5 ноября 2026 г.')
    expect(page.locator('.lesson')).to_have_count(6)
    assert not cache_errors, cache_errors
    cached.close()

    # PDF remains available without JavaScript.
    no_js = browser.new_context(java_script_enabled=False)
    page = no_js.new_page()
    page.goto(URL)
    expect(page.locator('noscript a')).to_have_text('Скачать расписание в PDF')
    expect(page.locator('noscript a')).to_be_visible()
    expect(page.locator('.pdf-card')).to_be_visible()
    no_js.close()
    browser.close()

print('Browser checks passed: mobile/desktop, timezone, live transitions, navigation, holidays, seasonal effects, reduced motion, PDF, and no-JS fallback.')
