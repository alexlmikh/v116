import assert from 'assert';
import { ROOMS } from '../schedule-data.js';
import { moscowNow, defaultDate, schoolDay, schoolWeek, dayState, lessonsFor } from '../schedule-time.js';

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

console.log('Schedule tests passed: Moscow dates, weekends, navigation, lesson boundaries, breaks, and Wednesday.');
