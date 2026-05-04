import { createPortal } from "react-dom";
import { CloseIcon } from "./Icons";
import { InstagramButton } from "./InstagramButton";
import { LEGENDS_GREEN } from "../constants/site";

type Link = { href: string; label: string };

type Props = {
  open: boolean;
  navLinks: readonly Link[];
  onClose: () => void;
};

function OverlayContent({ navLinks, onClose }: Omit<Props, "open">) {
  return (
    <div
      className="fixed inset-0 z-[10000] flex h-[100svh] min-h-[100svh] w-full max-w-none flex-col bg-[#0a0a0a] md:hidden"
      role="dialog"
      aria-modal="true"
      aria-label="Site menüsü"
    >
      <div
        className="flex shrink-0 items-center justify-between border-b border-white/10 px-5 py-4"
        style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}
      >
        <div>
          <div className="text-sm font-black tracking-[0.2em]" style={{ color: LEGENDS_GREEN }}>
            LEGENDS
          </div>
          <div className="text-xs text-white/65">Fitness</div>
        </div>
        <button
          type="button"
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/12 bg-white/5 text-white"
          onClick={onClose}
          aria-label="Menüyü kapat"
        >
          <CloseIcon className="h-5 w-5" />
        </button>
      </div>
      <nav
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-5 py-5"
        style={{
          WebkitOverflowScrolling: "touch",
          paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))",
        }}
      >
        {navLinks.map((l) => (
          <a
            key={l.href}
            href={l.href}
            className="rounded-2xl border border-white/10 bg-white/[0.05] px-5 py-4 text-base font-semibold active:bg-white/10"
            onClick={onClose}
          >
            {l.label}
          </a>
        ))}
        <div className="mt-auto border-t border-white/10 pt-6">
          <InstagramButton variant="footer" />
        </div>
      </nav>
    </div>
  );
}

/**
 * document.body üzerinde render — üst üste binme / kesilme olmaz; tam ekran garanti.
 */
export function MobileMenuOverlay({ open, navLinks, onClose }: Props) {
  if (!open || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <OverlayContent navLinks={navLinks} onClose={onClose} />,
    document.body,
  );
}
