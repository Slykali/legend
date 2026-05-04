export function getIstanbulWeekdayIndex(): number {
  const wd = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Istanbul",
    weekday: "short",
  }).format(new Date());
  const map: Record<string, number> = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
  };
  return map[wd] ?? 0;
}

export function getIstanbulMinutesNow(): number {
  const parts = new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Europe/Istanbul",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? "0");
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? "0");
  return hour * 60 + minute;
}

export function getLegendsOpenState(): {
  isOpen: boolean;
  label: string;
} {
  const day = getIstanbulWeekdayIndex();
  if (day === 0) {
    return { isOpen: false, label: "Kapalı · Pazar" };
  }
  const m = getIstanbulMinutesNow();
  const open = 6 * 60;
  const close = 23 * 60;
  const isOpen = m >= open && m < close;
  return {
    isOpen,
    label: isOpen ? "Açık" : "Kapalı",
  };
}
