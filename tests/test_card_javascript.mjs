import assert from "node:assert/strict";
import fs from "node:fs";

const helperSource = fs.readFileSync(
  new URL("../custom_components/aliexpress_package_tracker/dist/date_format.js", import.meta.url),
  "utf8"
);
const helperModule = await import(
  `data:text/javascript;base64,${Buffer.from(helperSource).toString("base64")}`
);
const { formatTimeForLocale } = helperModule;
const instant = "2026-09-16T13:05:00Z";
const config = { time_zone: "UTC" };

assert.equal(
  formatTimeForLocale(instant, { language: "en-US", date_format: "DMY", time_format: "24", time_zone: "server" }, config),
  "16/9/2026, 13:05"
);
assert.equal(
  formatTimeForLocale(instant, { language: "en-US", date_format: "MDY", time_format: "12", time_zone: "server" }, config),
  "9/16/2026, 01:05 PM"
);
assert.equal(
  formatTimeForLocale(instant, { language: "en-US", date_format: "YMD", time_format: "24", time_zone: "server" }, config),
  "2026/9/16, 13:05"
);
assert.equal(
  formatTimeForLocale("2026-09-16T01:05:00Z", { language: "en-US", date_format: "YMD", time_format: "24", time_zone: "server" }, { time_zone: "America/New_York" }),
  "2026/9/15, 21:05"
);
assert.equal(formatTimeForLocale("not-a-date", {}, config), "not-a-date");

const cardSource = fs.readFileSync(
  new URL("../custom_components/aliexpress_package_tracker/dist/aliexpress_package_card.js", import.meta.url),
  "utf8"
);
assert.match(cardSource, /if \(!customElements\.get\("aliexpress-package-card"\)\)/);
assert.match(cardSource, /if \(!customElements\.get\("aliexpress-package-card-editor"\)\)/);
assert.match(cardSource, /!window\.customCards\.some\(\(card\) => card\.type === "aliexpress-package-card"\)/);

console.log("JavaScript regression tests passed");
