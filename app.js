import { WEEKDAYS } from './schedule-data.js';
import { moscowNow, weekday, defaultDate, schoolDay, schoolWeek, formatDate, dayState, lessonCount } from './schedule-time.js';

const $ = id => document.getElementById(id);
const shortDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт'];
// An explicit preview URL freezes the first break, including on weekends.
const previewBreakTime = new URLSearchParams(window.location.search).has('previewBreak')
  ? new Date(`${defaultDate(moscowNow().date)}T09:20:00+03:00`)
  : null;
const readNow = () => previewBreakTime ? moscowNow(previewBreakTime) : moscowNow();
let now = readNow();
let selected = defaultDate(now.date);
let followToday = true;
let renderedDate = '';
let lastSignature = '';

function selectDate(date) {
  selected = date;
  followToday = date === defaultDate(readNow().date);
  render();
}

function renderCalendar() {
  const days = schoolWeek(selected);
  // Keep the focused weekday button in place across live clock updates.
  if ($('week').dataset.monday !== days[0]) {
    $('week').replaceChildren(...days.map((date, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.date = date;
      button.setAttribute('aria-label', `${WEEKDAYS[index]}, ${formatDate(date)}`);
      const name = document.createElement('span');
      name.textContent = shortDays[index];
      const number = document.createElement('strong');
      number.textContent = String(Number(date.slice(-2)));
      button.append(name, number);
      button.addEventListener('click', () => selectDate(date));
      return button;
    }));
    $('week').dataset.monday = days[0];
  }
  for (const button of $('week').children) {
    button.setAttribute('aria-pressed', String(button.dataset.date === selected));
    if (button.dataset.date === now.date) button.setAttribute('aria-current', 'date');
    else button.removeAttribute('aria-current');
  }
  const isWeekend = [0, 6].includes(weekday(now.date));
  const isToday = selected === now.date;
  $('day-name').textContent = WEEKDAYS[weekday(selected) - 1];
  $('full-date').textContent = formatDate(selected);
  $('relative-day').textContent = isToday ? 'Сегодня' : isWeekend && selected === defaultDate(now.date) ? 'Ближайший' : '';
  $('relative-day').hidden = !$('relative-day').textContent;
  $('today').textContent = isWeekend ? 'К ближайшему понедельнику' : 'К сегодняшнему дню';
  $('today').disabled = selected === defaultDate(now.date);
  $('weekend-notice').hidden = !isWeekend;
  $('weekend-notice').textContent = selected === defaultDate(now.date)
    ? `Сегодня выходной. Показываем ближайший понедельник, ${formatDate(selected)}`
    : `Сегодня выходной. Ближайший учебный день — понедельник, ${formatDate(defaultDate(now.date))}`;
}

function createRoomHint(roomNumber, tooltipId) {
  const hint = document.createElement('span');
  hint.className = 'room-hint';
  const tooltip = document.createElement('span');
  tooltip.className = 'room-tooltip';
  tooltip.id = tooltipId;
  tooltip.setAttribute('role', 'tooltip');
  tooltip.textContent = `${roomNumber.includes('/') ? 'Кабинеты' : 'Кабинет'} ${roomNumber.replaceAll(' / ', ' и ')}`;
  tooltip.hidden = true;
  const room = document.createElement('button');
  room.type = 'button';
  room.className = 'lesson-room';
  // The hint also names the button for screen readers, without repeating it.
  room.setAttribute('aria-labelledby', tooltip.id);
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M6 20V4h12v16M4 20h16M14 12h.01');
  icon.append(path);
  const rooms = document.createElement('span');
  rooms.className = 'room-number';
  rooms.setAttribute('aria-hidden', 'true');
  rooms.textContent = roomNumber;
  room.append(icon, rooms);
  hint.append(room, tooltip);
  hint.addEventListener('pointerenter', event => {
    if (event.pointerType === 'mouse') tooltip.hidden = false;
  });
  hint.addEventListener('pointerleave', () => {
    if (document.activeElement !== room) tooltip.hidden = true;
  });
  room.addEventListener('focus', () => {
    if (room.matches(':focus-visible')) tooltip.hidden = false;
  });
  room.addEventListener('blur', () => { tooltip.hidden = true; });
  room.addEventListener('click', event => {
    // Touch toggles the hint; keyboard activation keeps it open.
    tooltip.hidden = event.detail === 0 ? false : !tooltip.hidden;
  });
  return hint;
}

function renderLessons(state) {
  $('lessons').replaceChildren(...state.lessons.map((lesson, index) => {
    const item = document.createElement('li');
    item.className = 'lesson';
    item.dataset.number = lesson.number;
    const row = document.createElement('div');
    row.className = 'lesson-row';
    const number = document.createElement('span');
    number.className = 'lesson-number';
    number.textContent = lesson.number;
    number.setAttribute('aria-label', `${lesson.number}-й урок`);
    const content = document.createElement('div');
    content.className = 'lesson-content';
    const heading = document.createElement('div');
    heading.className = 'lesson-heading';
    const name = document.createElement('h3');
    name.textContent = lesson.name;
    const badge = document.createElement('span');
    badge.className = 'current-badge';
    badge.textContent = 'Сейчас';
    heading.append(name, badge);
    const time = document.createElement('p');
    time.className = 'lesson-time';
    time.textContent = `${lesson.start} — ${lesson.end}`;
    if (lesson.room) {
      heading.append(createRoomHint(lesson.room, `room-tooltip-${selected}-${lesson.number}`));
    }
    const progress = document.createElement('div');
    progress.className = 'progress';
    progress.setAttribute('aria-hidden', 'true');
    progress.append(document.createElement('span'));
    content.append(heading, time, progress);
    row.append(number, content);
    item.append(row);
    const next = state.lessons[index + 1];
    if (next) {
      const pause = document.createElement('p');
      pause.className = 'break-label';
      pause.textContent = `Перемена · ${(next.startSeconds - lesson.endSeconds) / 60} мин`;
      item.append(pause);
    }
    return item;
  }));
  renderedDate = selected;
}

function renderStatus(state) {
  let title, detail;
  if (state.kind === 'lesson') {
    title = `Идёт ${state.current.number}-й урок`;
    detail = `До конца ${state.minutes} мин · ${state.current.name}`;
  } else if (state.kind === 'break') {
    title = `Перемена · ещё ${state.minutes} мин`;
    detail = `Далее: ${state.next.name} в ${state.next.start}`;
  } else if (state.kind === 'before') {
    title = `Первый урок в ${state.next.start}`;
    detail = `До начала ${state.minutes} мин · ${state.next.name}`;
  } else if (state.kind === 'finished') {
    title = 'На сегодня всё!';
    detail = 'Уроки закончились. Можно выдохнуть.';
  } else {
    title = selected > now.date ? 'План на день' : 'Расписание за этот день';
    detail = `${lessonCount(state.lessons.length)} · с ${state.lessons[0].start} до ${state.lessons[state.lessons.length - 1].end}`;
  }
  $('live-status').dataset.state = state.kind;
  if ($('status-title').textContent !== title) $('status-title').textContent = title;
  if ($('status-detail').textContent !== detail) $('status-detail').textContent = detail;
  const room = state.current?.room || state.next?.room || '';
  const container = $('status-room');
  // Keep focus and open hints intact while the countdown refreshes.
  if (container.dataset.room !== room) {
    container.replaceChildren(...(room ? [createRoomHint(room, 'room-tooltip-status')] : []));
    container.dataset.room = room;
    container.hidden = !room;
  }
}

function render() {
  now = readNow();
  if (followToday) selected = defaultDate(now.date);
  $('clock').textContent = now.clock;
  $('clock').dateTime = `${now.date}T${now.clock}:00+03:00`;
  // Check every second for exact lesson boundaries, but update the DOM only as needed.
  const signature = `${selected}/${now.date}/${Math.floor(now.seconds / 60)}`;
  if (signature === lastSignature) return;
  lastSignature = signature;
  const state = dayState(selected, now);
  renderCalendar();
  if (renderedDate !== selected) renderLessons(state);
  renderStatus(state);
  $('day-summary').textContent = `${lessonCount(state.lessons.length)} · по 45 мин`;
  $('end-of-day').textContent = `Конец занятий в ${state.lessons[state.lessons.length - 1].end}`;
  for (const [index, item] of Array.from($('lessons').children).entries()) {
    const lesson = state.lessons[index];
    const active = state.current?.number === lesson.number;
    item.classList.toggle('is-current', active);
    item.classList.toggle('is-past', selected === now.date && now.seconds >= lesson.endSeconds);
    item.querySelector('.current-badge').hidden = !active;
    if (active) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
    item.querySelector('.progress span').style.width = active ? `${state.progress * 100}%` : '0';
    const pause = item.querySelector('.break-label');
    if (pause) {
      const currentBreak = state.kind === 'break'
        && state.lessons[index + 1]?.number === state.next.number;
      pause.classList.toggle('is-current-break', currentBreak);
      if (currentBreak) pause.setAttribute('aria-current', 'true');
      else pause.removeAttribute('aria-current');
    }
  }
  $('schedule').hidden = false;
}

$('preview-notice').hidden = !previewBreakTime;
$('previous').addEventListener('click', () => selectDate(schoolDay(selected, -1)));
$('next').addEventListener('click', () => selectDate(schoolDay(selected, 1)));
$('today').addEventListener('click', () => { followToday = true; render(); });
document.addEventListener('visibilitychange', () => { if (!document.hidden) render(); });
window.addEventListener('pageshow', render);
document.addEventListener('pointerdown', event => {
  for (const hint of document.querySelectorAll('.room-hint')) {
    if (!hint.contains(event.target)) hint.querySelector('.room-tooltip').hidden = true;
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    for (const tooltip of document.querySelectorAll('.room-tooltip')) tooltip.hidden = true;
  }
});
render();
setInterval(render, 1000);
