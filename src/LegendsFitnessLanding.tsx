import { motion, type Variants } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Container } from "./components/Container";
import { InstagramButton } from "./components/InstagramButton";
import { CloseIcon, MenuIcon, StarIcon } from "./components/Icons";
import {
  LEGENDS_BLACK,
  LEGENDS_CARD,
  LEGENDS_GREEN,
  ADDRESS,
  PHONE_DISPLAY,
  PHONE_HREF,
} from "./constants/site";
import { FEATURES, GALLERY, IMG, REVIEWS } from "./data/landingContent";
import { getLegendsOpenState } from "./lib/openingHours";
import { getMapsEmbedUrl, getGoogleDirectionsUrl } from "./lib/maps";

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] },
  },
};

const stagger: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.1, delayChildren: 0.08 },
  },
};

const heroStagger: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.14, delayChildren: 0.12 },
  },
};

const navLinks = [
  { href: "#hakkimizda", label: "Hakkımızda" },
  { href: "#ekipman", label: "Ekipman" },
  { href: "#yorumlar", label: "Yorumlar" },
  { href: "#galeri", label: "Galeri" },
  { href: "#iletisim", label: "İletişim" },
] as const;

export default function LegendsFitnessLanding() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openState, setOpenState] = useState(() => getLegendsOpenState());

  const directionsUrl = useMemo(() => getGoogleDirectionsUrl(), []);
  const embedUrl = useMemo(() => getMapsEmbedUrl(), []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpenState(getLegendsOpenState());
    const id = window.setInterval(() => setOpenState(getLegendsOpenState()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  const year = new Date().getFullYear();

  return (
    <div
      className="min-h-screen scroll-smooth bg-legends-bg font-sans text-white antialiased"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      {/* Arka plan dokusu */}
      <div
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_120%_80%_at_50%_-30%,rgba(57,211,83,0.12),transparent_55%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none fixed inset-0 -z-10 opacity-[0.035]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
        aria-hidden
      />

      <header
        className={`sticky top-0 z-50 border-b transition-[background,backdrop-filter,border-color] ${
          scrolled
            ? "border-white/10 bg-[#0a0a0a]/75 backdrop-blur-xl"
            : "border-transparent bg-transparent"
        }`}
      >
        <Container className="flex items-center justify-between py-4">
          <a
            href="#hero"
            className="group flex flex-col leading-none"
            onClick={() => setMobileOpen(false)}
          >
            <span
              className="text-lg font-black tracking-[0.22em] sm:text-xl"
              style={{ color: LEGENDS_GREEN }}
            >
              LEGENDS
            </span>
            <span className="text-xs font-semibold tracking-[0.35em] text-white/90 sm:text-sm">
              Fitness
            </span>
          </a>

          <nav className="hidden items-center gap-6 lg:gap-8 md:flex">
            {navLinks.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/55 transition hover:text-white"
              >
                {l.label}
              </a>
            ))}
            <InstagramButton variant="header" />
          </nav>

          <div className="flex items-center gap-2 md:hidden">
            <InstagramButton variant="header" />
            <button
              type="button"
              aria-label="Menüyü aç"
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 bg-white/[0.04] text-white"
              onClick={() => setMobileOpen(true)}
            >
              <MenuIcon className="h-5 w-5" />
            </button>
          </div>
        </Container>

        {mobileOpen ? (
          <div className="md:hidden">
            <div
              className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
              aria-hidden
            />
            <div className="fixed right-0 top-0 z-50 h-full w-[86%] max-w-sm border-l border-white/10 bg-[#0a0a0a]/95 backdrop-blur-2xl">
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <div>
                  <div className="text-sm font-black tracking-[0.2em]" style={{ color: LEGENDS_GREEN }}>
                    LEGENDS
                  </div>
                  <div className="text-xs text-white/65">Fitness</div>
                </div>
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/12 bg-white/5 text-white"
                  onClick={() => setMobileOpen(false)}
                  aria-label="Menüyü kapat"
                >
                  <CloseIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="flex flex-col gap-2 p-5">
                {navLinks.map((l) => (
                  <a
                    key={l.href}
                    href={l.href}
                    className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm font-semibold"
                    onClick={() => setMobileOpen(false)}
                  >
                    {l.label}
                  </a>
                ))}
                <div className="mt-2 border-t border-white/10 pt-4">
                  <InstagramButton variant="footer" />
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </header>

      {/* Hero */}
      <section id="hero" className="relative isolate min-h-[100svh] overflow-hidden">
        <img
          src={IMG.hero}
          alt="Legends Fitness salon"
          className="absolute inset-0 h-full w-full object-cover opacity-50"
          loading="eager"
        />
        <div
          className="absolute inset-0"
          style={{
            background: `linear-gradient(115deg, ${LEGENDS_GREEN}55 0%, rgba(10,10,10,0.92) 42%, ${LEGENDS_BLACK} 100%)`,
          }}
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(57,211,83,0.25),transparent_55%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_80%,rgba(57,211,83,0.08),transparent_45%)]" />

        <Container className="relative flex min-h-[100svh] flex-col justify-end pb-20 pt-28 sm:pb-28">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.35 }}
            variants={heroStagger}
            className="max-w-3xl"
          >
            <motion.div
              variants={fadeUp}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/45 px-4 py-2 text-sm backdrop-blur-md"
            >
              <span aria-hidden>⭐</span>
              <span className="font-black text-white">4.2</span>
              <span className="text-white/55">/ 67 yorum</span>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              className="mt-8 text-5xl font-black leading-[0.95] tracking-tight sm:text-7xl md:text-8xl"
            >
              Efsane Ol
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="mt-6 max-w-xl text-lg font-semibold leading-relaxed text-white/75 sm:text-xl"
            >
              4 Katlı · Geniş Ekipman · Uzman Kadro · Döşemealtı'nın Legends'ı
            </motion.p>

            <motion.div
              variants={fadeUp}
              className="mt-12 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center"
            >
              <a
                href="#iletisim"
                className="inline-flex items-center justify-center rounded-2xl px-10 py-4 text-sm font-black uppercase tracking-[0.14em] text-black shadow-[0_20px_50px_-15px_rgba(57,211,83,0.55)] transition hover:brightness-110"
                style={{ backgroundColor: LEGENDS_GREEN }}
              >
                Üye Ol
              </a>
              <a
                href={PHONE_HREF}
                className="inline-flex items-center justify-center rounded-2xl border-2 px-10 py-4 text-sm font-black uppercase tracking-[0.14em] text-white transition hover:bg-white/[0.06]"
                style={{ borderColor: "rgba(255,255,255,0.45)" }}
              >
                Bizi Ara
              </a>
              <InstagramButton variant="hero" />
            </motion.div>
          </motion.div>
        </Container>
      </section>

      {/* About */}
      <section id="hakkimizda" className="border-t border-white/[0.06] py-20 sm:py-24">
        <Container className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:items-center">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.25 }}
            variants={fadeUp}
            className="relative overflow-hidden rounded-3xl border border-white/10"
            style={{ backgroundColor: LEGENDS_CARD }}
          >
            <img
              src={IMG.about}
              alt="Legends Fitness iç mekân"
              className="h-[280px] w-full object-cover opacity-90 sm:h-[400px]"
              loading="lazy"
            />
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "linear-gradient(180deg, transparent 30%, rgba(10,10,10,0.9) 100%)",
              }}
            />
          </motion.div>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={stagger}
          >
            <motion.p
              variants={fadeUp}
              className="text-[10px] font-black uppercase tracking-[0.4em]"
              style={{ color: LEGENDS_GREEN }}
            >
              Hakkımızda
            </motion.p>
            <motion.h2
              variants={fadeUp}
              className="mt-4 text-3xl font-black tracking-tight sm:text-5xl"
            >
              Legends Fitness Hakkında
            </motion.h2>
            <motion.p variants={fadeUp} className="mt-6 text-base leading-8 text-white/65">
              Döşemealtı'nın Atatürk Bulvarı üzerinde 4 katlı yapısıyla öne çıkan Legends
              Fitness, geniş ekipman yelpazesi ve ilgili eğitmenleriyle her seviyeden
              sporsevere hitap ediyor. Kalabalık olmayan, temiz ve erişimi kolay bir spor
              merkezi. Uygun fiyat, kaliteli hizmet.
            </motion.p>
            <motion.div variants={fadeUp} className="mt-8 flex flex-wrap gap-2">
              {[
                "Ekipman çeşitliliği",
                "Antrenörler",
                "Ortam",
                "Personel",
                "Spor salonu kalitesi",
              ].map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-white/70"
                >
                  {tag}
                </span>
              ))}
            </motion.div>
          </motion.div>
        </Container>
      </section>

      {/* Features / Ekipman */}
      <section id="ekipman" className="pb-24 pt-4">
        <Container>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={stagger}
          >
            <motion.p
              variants={fadeUp}
              className="text-[10px] font-black uppercase tracking-[0.4em]"
              style={{ color: LEGENDS_GREEN }}
            >
              Legends deneyimi
            </motion.p>
            <motion.h2
              variants={fadeUp}
              className="mt-3 text-3xl font-black sm:text-4xl md:text-5xl"
            >
              Neden farklıyız?
            </motion.h2>
          </motion.div>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.1 }}
            variants={stagger}
            className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3"
          >
            {FEATURES.map((f) => (
              <motion.div
                key={f.title}
                variants={fadeUp}
                whileHover={{
                  y: -5,
                  boxShadow: `0 24px 60px -20px ${LEGENDS_GREEN}55`,
                  transition: { duration: 0.25 },
                }}
                className="relative overflow-hidden rounded-3xl border border-white/[0.07] p-6 transition-shadow"
                style={{ backgroundColor: LEGENDS_CARD }}
              >
                <div
                  className="absolute left-0 top-0 h-1 w-full"
                  style={{ backgroundColor: LEGENDS_GREEN }}
                />
                <div className="text-3xl">{f.emoji}</div>
                <h3 className="mt-4 text-lg font-black text-white">{f.title}</h3>
                <p className="mt-2 text-sm leading-7 text-white/55">{f.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </Container>
      </section>

      {/* Reviews */}
      <section id="yorumlar" className="border-t border-white/[0.06] py-20">
        <Container>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.25 }}
            variants={stagger}
          >
            <motion.p
              variants={fadeUp}
              className="text-[10px] font-black uppercase tracking-[0.4em]"
              style={{ color: LEGENDS_GREEN }}
            >
              Yorumlar
            </motion.p>
            <motion.h2
              variants={fadeUp}
              className="mt-3 text-3xl font-black sm:text-4xl"
            >
              Saha geri bildirimleri
            </motion.h2>
          </motion.div>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.15 }}
            variants={stagger}
            className="mt-10 flex gap-5 overflow-x-auto pb-4 [-webkit-overflow-scrolling:touch] [scrollbar-width:thin]"
          >
            {REVIEWS.map((r, i) => (
              <motion.article
                key={i}
                variants={fadeUp}
                className="min-w-[300px] max-w-md shrink-0 snap-start rounded-3xl border border-white/10 bg-white/[0.04] p-6 backdrop-blur-md"
              >
                <div className="flex gap-1" aria-label={`${r.stars} üzerinden 5 yıldız`}>
                  {Array.from({ length: r.stars }).map((_, j) => (
                    <StarIcon
                      key={j}
                      className="h-4 w-4"
                      filled
                      style={{ color: LEGENDS_GREEN }}
                    />
                  ))}
                  {Array.from({ length: 5 - r.stars }).map((_, j) => (
                    <StarIcon
                      key={`e-${j}`}
                      className="h-4 w-4 text-white/20"
                      filled={false}
                      style={{ color: LEGENDS_GREEN }}
                    />
                  ))}
                </div>
                <p className="mt-4 text-sm leading-7 text-white/80">{r.text}</p>
                <div className="mt-5 text-[10px] font-black uppercase tracking-[0.25em] text-white/45">
                  — {r.author}
                </div>
              </motion.article>
            ))}
          </motion.div>
        </Container>
      </section>

      {/* Gallery */}
      <section id="galeri" className="pb-24">
        <Container>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={stagger}
          >
            <motion.p
              variants={fadeUp}
              className="text-[10px] font-black uppercase tracking-[0.4em]"
              style={{ color: LEGENDS_GREEN }}
            >
              Galeri
            </motion.p>
            <motion.h2 variants={fadeUp} className="mt-3 text-3xl font-black sm:text-4xl">
              Mekân ve ekipman
            </motion.h2>
          </motion.div>

          <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {GALLERY.map((g, i) => (
              <motion.div
                key={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.15 }}
                variants={fadeUp}
                className="group relative overflow-hidden rounded-3xl border border-white/10 bg-[#0f0f0f]"
              >
                <img
                  src={g.src}
                  alt={g.hint}
                  className="h-52 w-full object-cover opacity-55 transition duration-500 ease-out group-hover:scale-110 group-hover:opacity-100 sm:h-56"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-90" />
                <div className="absolute inset-0 bg-black/55 transition-colors duration-300 group-hover:bg-[#39d353]/30" />
                <div className="pointer-events-none absolute bottom-3 left-3 right-3 rounded-2xl border border-white/10 bg-black/55 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white/90 backdrop-blur-sm">
                  {g.category}
                </div>
              </motion.div>
            ))}
          </div>
        </Container>
      </section>

      {/* Hours & location */}
      <section id="iletisim" className="border-t border-white/[0.06] pb-20 pt-16">
        <Container className="grid grid-cols-1 gap-8 lg:grid-cols-2 lg:items-stretch">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            variants={fadeUp}
            className="flex flex-col justify-center rounded-3xl border border-white/[0.08] p-8 sm:p-10"
            style={{ backgroundColor: LEGENDS_CARD }}
          >
            <p className="text-[10px] font-black uppercase tracking-[0.35em] text-white/45">
              Çalışma saatleri
            </p>
            <h2 className="mt-4 text-2xl font-black sm:text-3xl">
              Pzt–Cmt: 06:00–23:00
            </h2>
            <p className="mt-2 text-white/55">Pazar: Kapalı</p>
            <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-white/40">
              Pazar günleri kapalıdır
            </p>
            <div className="mt-8 inline-flex flex-wrap items-center gap-4 rounded-2xl border border-white/10 bg-black/35 px-4 py-4">
              <span
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-[11px] font-black uppercase"
                style={{
                  background: openState.isOpen
                    ? "rgba(57,211,83,0.15)"
                    : "rgba(255,255,255,0.08)",
                  border: `1px solid ${openState.isOpen ? "rgba(57,211,83,0.45)" : "rgba(255,255,255,0.14)"}`,
                  color: openState.isOpen ? LEGENDS_GREEN : "rgba(255,255,255,0.55)",
                }}
              >
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{
                    background: openState.isOpen ? LEGENDS_GREEN : "rgba(255,255,255,0.35)",
                  }}
                />
                {openState.label}
              </span>
              <span className="text-sm font-medium text-white/60">
                Türkiye saati · İstanbul
              </span>
            </div>
            <p className="mt-10 text-[10px] font-black uppercase tracking-[0.3em] text-white/35">
              Adres
            </p>
            <p className="mt-2 text-base leading-8 text-white/70">{ADDRESS}</p>
            <a
              href={PHONE_HREF}
              className="mt-6 inline-flex text-lg font-black"
              style={{ color: LEGENDS_GREEN }}
            >
              {PHONE_DISPLAY}
            </a>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={fadeUp}
            className="relative min-h-[360px] overflow-hidden rounded-3xl border border-white/[0.08]"
            style={{ backgroundColor: LEGENDS_CARD }}
          >
            <iframe
              title="Legends Fitness harita"
              src={embedUrl}
              className="absolute inset-0 h-full min-h-[360px] w-full"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </motion.div>
        </Container>
      </section>

      {/* Contact CTA */}
      <section className="border-t border-white/[0.06] bg-black/40 pb-24 pt-16">
        <Container>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.35 }}
            variants={fadeUp}
            className="relative overflow-hidden rounded-[2rem] border border-white/10 p-10 sm:p-14"
            style={{ backgroundColor: LEGENDS_BLACK }}
          >
            <div
              className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full blur-3xl"
              style={{ background: `${LEGENDS_GREEN}33` }}
            />
            <div className="relative max-w-2xl">
              <h2 className="text-3xl font-black sm:text-5xl">Efsaneye Katıl</h2>
              <p className="mt-4 text-sm text-white/55">
                Hemen ara, yol tarifi al veya Instagram'dan güncel kal — Atatürk Bulvarı
                Legends Fitness.
              </p>
            </div>
            <div className="relative mt-10 flex flex-col gap-4 sm:flex-row sm:flex-wrap">
              <a
                href={PHONE_HREF}
                className="inline-flex flex-1 items-center justify-center rounded-2xl px-8 py-4 text-center text-sm font-black uppercase tracking-[0.12em] text-black sm:flex-none sm:px-12"
                style={{ backgroundColor: LEGENDS_GREEN }}
              >
                Hemen Ara
              </a>
              <a
                href={directionsUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex flex-1 items-center justify-center rounded-2xl border-2 px-8 py-4 text-center text-sm font-black uppercase tracking-[0.12em] text-white sm:flex-none sm:px-12"
                style={{ borderColor: "rgba(255,255,255,0.5)" }}
              >
                Google Haritalar yön tarifi
              </a>
              <InstagramButton variant="hero" />
            </div>
          </motion.div>
        </Container>
      </section>

      <footer className="border-t border-white/[0.06] pb-12 pt-10">
        <Container className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="font-bold text-white/80">
            Legends Fitness · Döşemealtı / Antalya 🏆💪
          </div>
          <div className="flex flex-col items-start gap-3 text-sm text-white/55 sm:items-end">
            <InstagramButton variant="footer" />
            <div className="flex flex-col gap-1 text-xs text-white/40">
              <span>© {year} Legends Fitness</span>
              <span>Pzt–Cmt 06:00–23:00 · Pazar Kapalı</span>
            </div>
          </div>
        </Container>
      </footer>
    </div>
  );
}
