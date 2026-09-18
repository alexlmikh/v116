"""Browser checks: pip install playwright; uses installed Google Chrome.

Start `python3 -m http.server 8765` first, then run
`python3 tests/schedule-browser.py [URL]`. Screenshots go to /tmp.
"""
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import hashlib
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
    assert not errors, errors
    context.close()

    desktop = browser.new_context(viewport={'width': 390, 'height': 844})
    page = desktop.new_page()
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

    # PDF remains available without JavaScript.
    no_js = browser.new_context(java_script_enabled=False)
    page = no_js.new_page()
    page.goto(URL)
    expect(page.locator('noscript a')).to_have_text('Скачать расписание в PDF')
    expect(page.locator('noscript a')).to_be_visible()
    expect(page.locator('.pdf-card')).to_be_visible()
    no_js.close()
    browser.close()

print('Browser checks passed: mobile/desktop, timezone, live transitions, navigation, weekends, midnight, PDF, and no-JS fallback.')
