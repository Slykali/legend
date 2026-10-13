import { useId } from "react";

/** React's useId() contains colons, which are awkward inside url(#...) references. */
function useSvgId(prefix: string): string {
  return `${prefix}-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
}

// Bell mark drawn on a 32x32 grid (shared by Logo, EmptyIllustration and public/icon.svg).
const BELL_BODY =
  "M16 5.2c-4.6 0-7.9 3.5-7.9 8.1v4.3c0 1.4-.6 2.7-1.6 3.6l-.8.7c-.8.7-.3 2 .8 2h19c1.1 0 1.6-1.3.8-2l-.8-.7c-1-.9-1.6-2.2-1.6-3.6v-4.3c0-4.6-3.3-8.1-7.9-8.1Z";
const BELL_CLAPPER = "M12.9 25.4a3.1 3.1 0 0 0 6.2 0Z";
const BELL_SHINE = "M11.3 12.8c.3-2 1.5-3.6 3.3-4.3";
const DOT = { cx: 24.8, cy: 7.2, r: 3.4, cut: 5.3 };

function BellMark({ gradId, maskId }: { gradId: string; maskId: string }) {
  return (
    <>
      <defs>
        <linearGradient id={gradId} x1="6" y1="27" x2="26" y2="4" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#7c5cff" />
          <stop offset="1" stopColor="#a78bfa" />
        </linearGradient>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="32" height="32">
          <rect width="32" height="32" fill="#fff" />
          <circle cx={DOT.cx} cy={DOT.cy} r={DOT.cut} fill="#000" />
        </mask>
      </defs>
      <g mask={`url(#${maskId})`} fill={`url(#${gradId})`}>
        <circle cx="16" cy="4.6" r="1.7" />
        <path d={BELL_BODY} />
        <path d={BELL_CLAPPER} />
      </g>
      <path d={BELL_SHINE} fill="none" stroke="#fff" strokeOpacity=".5" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx={DOT.cx} cy={DOT.cy} r={DOT.r} fill="#34d399" />
    </>
  );
}

/** App mark: violet gradient bell with a green "ready" dot. Readable from 16-24px up. */
export function Logo({ className }: { className?: string }) {
  const gradId = useSvgId("logo-grad");
  const maskId = useSvgId("logo-mask");
  return (
    <svg
      viewBox="0 0 32 32"
      className={className ?? "h-7 w-7"}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <BellMark gradId={gradId} maskId={maskId} />
    </svg>
  );
}

/** Four-point sparkle centred on (cx, cy). */
function sparkle(cx: number, cy: number, r: number): string {
  return `M${cx} ${cy - r}Q${cx} ${cy} ${cx + r} ${cy}Q${cx} ${cy} ${cx} ${cy + r}Q${cx} ${cy} ${cx - r} ${cy}Q${cx} ${cy} ${cx} ${cy - r}Z`;
}

const GRID_X = [59, 81, 103, 125];
const GRID_Y = [70, 88, 106];

/** Decorative empty-state art: a calendar card with a ringing bell and soft sparkles. */
export function EmptyIllustration({ className }: { className?: string }) {
  const glowId = useSvgId("empty-glow");
  const headId = useSvgId("empty-head");
  const clipId = useSvgId("empty-clip");
  const bellGradId = useSvgId("empty-bell-grad");
  const bellMaskId = useSvgId("empty-bell-mask");

  return (
    <svg
      viewBox="0 0 200 160"
      className={className ?? "h-32 w-40"}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient id={glowId} cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(100 84) scale(84)">
          <stop offset="0" stopColor="#7c5cff" stopOpacity=".28" />
          <stop offset="1" stopColor="#7c5cff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={headId} x1="48" y1="36" x2="152" y2="60" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#7c5cff" />
          <stop offset="1" stopColor="#a78bfa" />
        </linearGradient>
        <clipPath id={clipId}>
          <rect x="48" y="36" width="104" height="96" rx="16" />
        </clipPath>
      </defs>

      {/* soft glow + floor shadow */}
      <circle cx="100" cy="84" r="84" fill={`url(#${glowId})`} />
      <ellipse cx="100" cy="141" rx="50" ry="5" fill="#000" fillOpacity=".3" />

      {/* calendar card */}
      <rect x="48" y="36" width="104" height="96" rx="16" fill="#1c2130" />
      <g clipPath={`url(#${clipId})`}>
        <rect x="48" y="36" width="104" height="24" fill={`url(#${headId})`} />
        <rect x="60" y="45" width="30" height="6" rx="3" fill="#fff" fillOpacity=".55" />
      </g>
      <rect x="49" y="37" width="102" height="94" rx="15" stroke="#2a3142" strokeWidth="2" />

      {/* binder rings */}
      <rect x="70" y="28" width="8" height="16" rx="4" fill="#141821" stroke="#2a3142" strokeWidth="2" />
      <rect x="104" y="28" width="8" height="16" rx="4" fill="#141821" stroke="#2a3142" strokeWidth="2" />

      {/* day grid */}
      {GRID_Y.map((y, row) =>
        GRID_X.map((x, col) => {
          const key = `${row}-${col}`;
          if (row === 0 && col === 1) {
            return (
              <g key={key}>
                <rect x={x} y={y} width="16" height="13" rx="3.5" fill="#34d399" fillOpacity=".18" />
                <path
                  d={`M${x + 4.5} ${y + 6.8}l2.5 2.4 4.6-5`}
                  stroke="#34d399"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </g>
            );
          }
          if (row === 1 && col === 2) {
            return <rect key={key} x={x} y={y} width="16" height="13" rx="3.5" fill="#7c5cff" />;
          }
          return <rect key={key} x={x} y={y} width="16" height="13" rx="3.5" fill="#2a3142" fillOpacity={row === 2 && col > 1 ? 0.5 : 1} />;
        }),
      )}

      {/* bell badge */}
      <circle cx="154" cy="36" r="23" fill="#141821" stroke="#2a3142" strokeWidth="2" />
      <g transform="translate(134 16.6) scale(1.25) rotate(-12 16 15.5)">
        <BellMark gradId={bellGradId} maskId={bellMaskId} />
      </g>
      <path d="M181 26.5c2.6 2.8 3.9 6 3.9 9.5" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" strokeOpacity=".7" />
      <path d="M186.5 21.5c3.8 4.1 5.6 8.9 5.6 14" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" strokeOpacity=".4" />

      {/* sparkles + dots */}
      <path d={sparkle(30, 56, 7)} fill="#a78bfa" />
      <path d={sparkle(174, 102, 5)} fill="#7c5cff" />
      <path d={sparkle(28, 112, 4)} fill="#34d399" fillOpacity=".8" />
      <circle cx="42" cy="30" r="3" fill="#7c5cff" fillOpacity=".6" />
      <circle cx="168" cy="128" r="3.5" fill="#34d399" fillOpacity=".6" />
      <circle cx="16" cy="84" r="2.5" fill="#a78bfa" fillOpacity=".5" />
    </svg>
  );
}
