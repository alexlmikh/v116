import { BELL_TIMES, LESSONS, ROOMS } from './schedule-data.js';
import { HOLIDAYS } from './holiday-data.js';
import { PUBLIC_HOLIDAYS } from './public-holiday-data.js';

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
  let date = today;
  let holiday = holidayFor(date);
  while (holiday || publicHolidayFor(date) || [0, 6].includes(weekday(date))) {
    date = shiftDate(holiday ? holidayBounds(holiday).end : date, 1);
    holiday = holidayFor(date);
  }
  return date;
}

export function schoolDay(date, direction) {
  // Browse every weekday, including days off, to keep the usual timetable accessible.
  let next = shiftDate(date, direction);
  while (weekday(next) === 0 || weekday(next) === 6) next = shiftDate(next, direction);
  return next;
}

export function schoolWeek(date) {
  const monday = shiftDate(date, -((weekday(date) + 6) % 7));
  return Array.from({ length: 5 }, (_, index) => shiftDate(monday, index));
}

export function formatDate(date) {
  return calendar.format(new Date(`${date}T12:00:00Z`));
}

export function holidayBounds(holiday) {
  let { start, end } = holiday;
  while ([0, 6].includes(weekday(shiftDate(start, -1)))) start = shiftDate(start, -1);
  while ([0, 6].includes(weekday(shiftDate(end, 1)))) end = shiftDate(end, 1);
  return { start, end };
}

export function holidayFor(date) {
  return HOLIDAYS.find(holiday => {
    const { start, end } = holidayBounds(holiday);
    return date >= start && date <= end;
  });
}

export function publicHolidayFor(date) {
  return PUBLIC_HOLIDAYS[date];
}

export function holidayDates(holiday) {
  const start = formatDate(holiday.start).replace(/ г\.$/, '');
  const end = formatDate(holiday.end).replace(/ г\.$/, '');
  return `${holiday.start.slice(0, 4) === holiday.end.slice(0, 4) ? start.replace(/ \d{4}$/, '') : start} – ${end}`;
}

export function holidayDuration(holiday) {
  const days = Math.round((new Date(`${holiday.end}T12:00:00Z`) - new Date(`${holiday.start}T12:00:00Z`)) / 86400000) + 1;
  const word = days % 10 === 1 && days % 100 !== 11 ? 'день'
    : [2, 3, 4].includes(days % 10) && ![12, 13, 14].includes(days % 100) ? 'дня' : 'дней';
  return `${days} ${word}`;
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
  const holiday = holidayFor(date);
  const lessons = lessonsFor(date);
  // Keep the usual weekday timetable available as a reference, without live tracking.
  if (holiday) return { kind: 'holiday', holiday, lessons };
  const publicHoliday = publicHolidayFor(date);
  if (publicHoliday) return { kind: 'public-holiday', publicHoliday, lessons };
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
