import { INSTAGRAM_URL } from "../constants/site";
import { InstagramGlyph } from "./Icons";

type Variant = "header" | "hero" | "footer";

const variantClass: Record<Variant, string> = {
  header:
    "h-11 w-11 rounded-xl border border-white/15 bg-white/[0.04] text-white transition hover:border-[#E4405F]/50 hover:bg-[#E4405F]/10 hover:text-white",
  hero:
    "inline-flex items-center justify-center gap-2.5 rounded-2xl border border-white/20 bg-white/[0.06] px-8 py-4 text-sm font-black uppercase tracking-[0.1em] text-white backdrop-blur-sm transition hover:border-[#E4405F]/40 hover:bg-[#E4405F]/15",
  footer:
    "inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-4 py-2 text-xs font-bold text-white/80 transition hover:border-[#E4405F]/40 hover:text-white",
};

export function InstagramButton({ variant }: { variant: Variant }) {
  return (
    <a
      href={INSTAGRAM_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={variantClass[variant]}
      aria-label="Legends Fitness Instagram"
    >
      <InstagramGlyph
        className={variant === "header" ? "h-5 w-5" : "h-5 w-5 shrink-0"}
      />
      {variant !== "header" ? (
        <span>{variant === "hero" ? "Instagram'da takip et" : "Instagram"}</span>
      ) : null}
    </a>
  );
}
