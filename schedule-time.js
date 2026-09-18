import { BELL_TIMES, LESSONS, ROOMS } from './schedule-data.js';

export const TIME_ZONE = 'Europe/Moscow';
const clock = new Intl.DateTimeFormat('en-GB', {
  timeZone: TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
});
const calendar = new Intl.DateTimeFormat('ru-RU', {
  timeZone: 'UTC', day: 'numeric', month: 'long', year: 'numeric',
});

// Calendar arithmetic uses UTC dates, never the device's local timezone.
export function moscowNow(instant = new Date()) {
  const parts = Object.fromEntries(clock.formatToParts(instant).map(p => [p.type, p.value]));
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    seconds: Number(parts.hour) * 3600 + Number(parts.minute) * 60 + Number(parts.second),
    clock: `${parts.hour}:${parts.minute}`,
  };
}

export function weekday(date) {
  return new Date(`${date}T12:00:00Z`).getUTCDay();
}

export function shiftDate(date, days) {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export function defaultDate(today) {
  const day = weekday(today);
  return day === 6 ? shiftDate(today, 2) : day === 0 ? shiftDate(today, 1) : today;
}

export function schoolDay(date, direction) {
  let next = shiftDate(date, direction);
  while (weekday(next) === 0 || weekday(next) === 6) next = shiftDate(next, direction);
  return next;
}

export function schoolWeek(date) {
  const monday = shiftDate(date, 1 - weekday(date));
  return Array.from({ length: 5 }, (_, index) => shiftDate(monday, index));
}

export function formatDate(date) {
  return calendar.format(new Date(`${date}T12:00:00Z`));
}

export function timeSeconds(time) {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 3600 + minutes * 60;
}

export function lessonsFor(date) {
  const day = weekday(date) - 1;
  return (LESSONS[day] || []).flatMap((name, index) => name ? [{
    number: index + 1, name, room: ROOMS[day][index],
    start: BELL_TIMES[index][0], end: BELL_TIMES[index][1],
    startSeconds: timeSeconds(BELL_TIMES[index][0]),
    endSeconds: timeSeconds(BELL_TIMES[index][1]),
  }] : []);
}

export function dayState(date, now) {
  const lessons = lessonsFor(date);
  if (date !== now.date) return { kind: 'preview', lessons };
  const current = lessons.find(lesson => now.seconds >= lesson.startSeconds && now.seconds < lesson.endSeconds);
  if (current) return {
    kind: 'lesson', lessons, current,
    minutes: Math.ceil((current.endSeconds - now.seconds) / 60),
    progress: (now.seconds - current.startSeconds) / (current.endSeconds - current.startSeconds),
  };
  const next = lessons.find(lesson => lesson.startSeconds > now.seconds);
  if (next) return {
    kind: next.number === lessons[0].number ? 'before' : 'break', lessons, next,
    minutes: Math.ceil((next.startSeconds - now.seconds) / 60),
  };
  return { kind: 'finished', lessons };
}

export function lessonCount(count) {
  return `${count} ${count === 5 || count === 6 ? 'уроков' : 'урока'}`;
}
