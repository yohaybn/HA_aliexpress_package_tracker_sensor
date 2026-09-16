export function formatTimeForLocale(value, locale = {}, config = {}) {
  if (!value) return null;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  const language = locale.date_format === "system" ? undefined : locale.language;
  const timeZone = locale.time_zone === "local" ? undefined : config.time_zone;
  const dateOptions = {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    ...(timeZone ? { timeZone } : {}),
  };
  const dateFormatter = new Intl.DateTimeFormat(language, dateOptions);
  let formattedDate;

  if (["DMY", "MDY", "YMD"].includes(locale.date_format)) {
    const parts = Object.fromEntries(
      dateFormatter
        .formatToParts(date)
        .filter((part) => ["day", "month", "year"].includes(part.type))
        .map((part) => [part.type, part.value])
    );
    const order = {
      DMY: ["day", "month", "year"],
      MDY: ["month", "day", "year"],
      YMD: ["year", "month", "day"],
    }[locale.date_format];
    formattedDate = order.map((part) => parts[part]).join("/");
  } else {
    formattedDate = dateFormatter.format(date);
  }

  let hour12;
  if (locale.time_format === "12") hour12 = true;
  if (locale.time_format === "24") hour12 = false;
  const timeFormatter = new Intl.DateTimeFormat(
    locale.time_format === "system" ? undefined : locale.language,
    {
      hour: "2-digit",
      minute: "2-digit",
      ...(hour12 === undefined ? {} : { hour12 }),
      ...(timeZone ? { timeZone } : {}),
    }
  );

  return `${formattedDate}, ${timeFormatter.format(date)}`;
}
