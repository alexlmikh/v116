// Russia's federal non-working holidays and transferred days off for 2026 only.
// Ordinary Saturdays/Sundays are handled by the schedule date helpers.
// Sources (verified 2026-10-24):
// https://www.cbr.ru/other/holidays/ (2026 section; includes statutory transfers)
// https://publication.pravo.gov.ru/document/0001202509240023
// Government decree of 24 September 2025, No. 1466: Jan 3 -> Jan 9, Jan 4 -> Dec 31.
// Commemorative dates and shortened working days are deliberately excluded.
export const PUBLIC_HOLIDAYS = {
  '2026-01-01': 'Новогодние каникулы',
  '2026-01-02': 'Новогодние каникулы',
  '2026-01-03': 'Новогодние каникулы',
  '2026-01-04': 'Новогодние каникулы',
  '2026-01-05': 'Новогодние каникулы',
  '2026-01-06': 'Новогодние каникулы',
  '2026-01-07': 'Рождество Христово',
  '2026-01-08': 'Новогодние каникулы',
  '2026-01-09': 'Перенесённый выходной за 3 января',
  '2026-02-23': 'День защитника Отечества',
  '2026-03-08': 'Международный женский день',
  '2026-03-09': 'Перенесённый выходной за 8 марта',
  '2026-05-01': 'Праздник Весны и Труда',
  '2026-05-09': 'День Победы',
  '2026-05-11': 'Перенесённый выходной за 9 мая',
  '2026-06-12': 'День России',
  '2026-11-04': 'День народного единства',
  '2026-12-31': 'Перенесённый выходной за 4 января',
};
