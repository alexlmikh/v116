import assert from 'assert';
import { ROOMS } from '../schedule-data.js';
import { HOLIDAYS } from '../holiday-data.js';
import { PUBLIC_HOLIDAYS } from '../public-holiday-data.js';
import { moscowNow, defaultDate, schoolDay, schoolWeek, dayState, lessonsFor, holidayFor, holidayBounds, holidayDates, holidayDuration, shiftDate, publicHolidayFor, weekday } from '../schedule-time.js';

const friday = '2026-09-11';
const at = time => moscowNow(new Date(`${friday}T${time}+03:00`));
const state = time => dayState(friday, at(time));

assert.deepStrictEqual(moscowNow(new Date('2026-09-11T21:00:00Z')), {
  date: '2026-09-12', clock: '00:00', seconds: 0,
});
assert.strictEqual(defaultDate(friday), friday);
assert.strictEqual(defaultDate('2026-09-12'), '2026-09-14');
assert.strictEqual(defaultDate('2026-09-13'), '2026-09-14');
assert.strictEqual(defaultDate('2026-09-14'), '2026-09-14');
assert.strictEqual(defaultDate('2022-12-31'), '2023-01-02');
assert.strictEqual(schoolDay(friday, 1), '2026-09-14');
assert.strictEqual(schoolDay('2026-09-14', -1), friday);
assert.strictEqual(schoolDay('2026-01-01', -1), '2025-12-31');
assert.deepStrictEqual(schoolWeek('2026-10-01'), [
  '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02',
]);
assert.strictEqual(state('08:29:59').kind, 'before');
assert.strictEqual(state('08:29:59').minutes, 1);
assert.strictEqual(state('08:30:00').current.number, 1);
assert.strictEqual(state('08:30:00').progress, 0);
assert.strictEqual(state('09:14:59').current.number, 1);
assert.strictEqual(state('09:14:59').minutes, 1);
assert.strictEqual(state('09:15:00').kind, 'break');
assert.strictEqual(state('09:15:00').minutes, 10);
assert.strictEqual(state('09:15:00').next.number, 2);
assert.strictEqual(state('09:25:00').current.number, 2);
assert.strictEqual(state('14:19:59').current.number, 6);
assert.strictEqual(state('14:20:00').kind, 'finished');
assert.strictEqual(dayState('2026-09-14', at('08:45:00')).kind, 'preview');
assert.strictEqual(dayState('2026-09-10', at('08:45:00')).kind, 'preview');
assert.strictEqual(lessonsFor('2026-09-09').length, 6);
assert.strictEqual(lessonsFor('2026-09-09')[5].name, 'География');
assert.strictEqual(lessonsFor('2026-09-09')[5].room, '426');
assert.deepStrictEqual(ROOMS, [
  ['', '103 / 320', '422', '324', '324', ''],
  ['325', '103 / 320', '325', '', '324', '325'],
  ['103 / 320', '325', '325', '422', '324', '426'],
  ['325', '325', '202', '324', '213', '212'],
  ['103 / 320', '325', '322', '324', '422', '423'],
]);
const wednesdayState = time => dayState('2026-09-09', moscowNow(new Date(`2026-09-09T${time}+03:00`)));
assert.strictEqual(wednesdayState('13:25:00').kind, 'break');
assert.strictEqual(wednesdayState('13:25:00').next.number, 6);
assert.strictEqual(wednesdayState('13:35:00').current.name, 'География');
assert.strictEqual(wednesdayState('14:19:59').current.number, 6);
assert.strictEqual(wednesdayState('14:20:00').kind, 'finished');
assert.strictEqual(dayState('2026-09-14', moscowNow(new Date('2026-09-12T08:45:00+03:00'))).kind, 'preview');
assert.strictEqual(lessonsFor('2026-09-12').length, 0);

// Official dates remain exact; holiday dates have no live lesson tracking.
const holidayCases = [
  ['autumn', '2026-10-24', '2026-11-03', '26 октября – 3 ноября 2026', '9 дней', '2026-11-05'],
  ['winter', '2026-12-31', '2027-01-10', '31 декабря 2026 – 10 января 2027', '11 дней', '2027-01-11'],
  ['spring', '2027-03-27', '2027-04-04', '27 марта – 4 апреля 2027', '9 дней', '2027-04-05'],
  ['summer', '2027-05-27', '2027-08-31', '27 мая – 31 августа 2027', '97 дней', '2027-09-01'],
];
for (const [season, start, end, label, duration, resume] of holidayCases) {
  const holiday = HOLIDAYS.find(item => item.season === season);
  assert.deepStrictEqual(holidayBounds(holiday), { start, end });
  assert.strictEqual(holidayDates(holiday), label);
  assert.strictEqual(holidayDuration(holiday), duration);
  assert.strictEqual(holidayFor(shiftDate(start, -1)), undefined);
  assert.strictEqual(holidayFor(shiftDate(end, 1)), undefined);
  for (let date = start; date <= end; date = shiftDate(date, 1)) {
    assert.strictEqual(defaultDate(date), resume);
    const result = dayState(date, moscowNow(new Date(`${date}T08:45:00+03:00`)));
    assert.deepStrictEqual(result, { kind: 'holiday', holiday, lessons: lessonsFor(date) });
    assert.strictEqual(dayState(defaultDate(date), moscowNow(new Date(`${date}T08:45:00+03:00`))).kind, 'preview');
    assert.strictEqual(dayState(date, at('08:45:00')).kind, 'holiday');
  }
  assert.strictEqual(dayState(resume, moscowNow(new Date(`${resume}T08:45:00+03:00`))).kind, 'lesson');
}
// Friday endings include both following weekend days, Sunday starts include Saturday.
// The supplied year has no Friday endings, so exercise that rule independently.
assert.deepStrictEqual(holidayBounds({ start: '2026-10-26', end: '2026-10-30' }), {
  start: '2026-10-24', end: '2026-11-01',
});
assert.deepStrictEqual(holidayBounds({ start: '2026-10-25', end: '2026-10-31' }), {
  start: '2026-10-24', end: '2026-11-01',
});
assert.deepStrictEqual(schoolWeek('2026-10-25'), schoolWeek('2026-10-19'));
assert.strictEqual(holidayFor(moscowNow(new Date('2026-10-23T20:59:59Z')).date), undefined);
assert.strictEqual(holidayFor(moscowNow(new Date('2026-10-23T21:00:00Z')).date).season, 'autumn');
assert.strictEqual(holidayFor('2027-10-26'), undefined); // Holidays do not repeat annually.

// The official 2026 calendar has 14 statutory dates and four transferred days off.
assert.deepStrictEqual(Object.keys(PUBLIC_HOLIDAYS), [
  '2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05',
  '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-02-23',
  '2026-03-08', '2026-03-09', '2026-05-01', '2026-05-09', '2026-05-11',
  '2026-06-12', '2026-11-04', '2026-12-31',
]);
for (const date of Object.keys(PUBLIC_HOLIDAYS)) {
  assert.ok(defaultDate(date) > date);
  for (const time of ['08:00:00', '08:45:00', '09:20:00', '12:00:00', '15:00:00']) {
    const result = dayState(date, moscowNow(new Date(`${date}T${time}+03:00`)));
    assert.ok(['holiday', 'public-holiday'].includes(result.kind));
    assert.strictEqual(result.current, undefined);
    assert.strictEqual(result.next, undefined);
    assert.strictEqual(result.progress, undefined);
    assert.strictEqual(result.minutes, undefined);
  }
}
for (const [date, next] of [
  ['2026-01-01', '2026-01-12'], ['2026-01-09', '2026-01-12'],
  ['2026-02-21', '2026-02-24'], ['2026-03-07', '2026-03-10'],
  ['2026-05-01', '2026-05-04'], ['2026-05-09', '2026-05-12'],
  ['2026-06-12', '2026-06-15'], ['2026-11-04', '2026-11-05'],
  ['2026-12-31', '2027-01-11'],
]) assert.strictEqual(defaultDate(date), next);
let nonWorkingDays = 0;
for (let date = '2026-01-01'; date <= '2026-12-31'; date = shiftDate(date, 1)) {
  if (publicHolidayFor(date) || [0, 6].includes(weekday(date))) nonWorkingDays++;
}
assert.strictEqual(nonWorkingDays, 118); // Federal five-day calendar, excluding school breaks.
for (const date of ['2026-04-30', '2026-05-08', '2026-06-11', '2026-10-05']) {
  assert.strictEqual(publicHolidayFor(date), undefined); // Shortened days and observances stay working.
  assert.strictEqual(defaultDate(date), date);
}
assert.strictEqual(publicHolidayFor('2026-11-03'), undefined);
assert.strictEqual(publicHolidayFor('2027-11-04'), undefined); // Never reuse a year's transfer calendar.
assert.strictEqual(publicHolidayFor(moscowNow(new Date('2026-11-03T20:59:59Z')).date), undefined);
assert.strictEqual(publicHolidayFor(moscowNow(new Date('2026-11-03T21:00:00Z')).date), 'День народного единства');

console.log('Schedule tests passed: Moscow dates, navigation, lessons, school holidays, and the official 2026 non-working calendar.');
