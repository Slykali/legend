export const IMG = {
  hero: "https://lh3.googleusercontent.com/placeholder-legend-hero",
  about: "https://lh3.googleusercontent.com/placeholder-legend-about",
  g1: "https://lh3.googleusercontent.com/placeholder-gallery-1",
  g2: "https://lh3.googleusercontent.com/placeholder-gallery-2",
  g3: "https://lh3.googleusercontent.com/placeholder-gallery-3",
  g4: "https://lh3.googleusercontent.com/placeholder-gallery-4",
  g5: "https://lh3.googleusercontent.com/placeholder-gallery-5",
  g6: "https://lh3.googleusercontent.com/placeholder-gallery-6",
} as const;

export const FEATURES = [
  {
    emoji: "🏢",
    title: "4 Katlı Geniş Alan",
    desc: "Katlar arasında dağılan alan ile kalabalık hissi yok; antrenmana odaklan.",
  },
  {
    emoji: "🏋️",
    title: "Geniş Ekipman Yelpazesi",
    desc: "Çeşitli istasyonlar; güç, kardiyo ve yardımcı aksesuarlar bol seçenekli.",
  },
  {
    emoji: "👨‍🏫",
    title: "Uzman Eğitmenler",
    desc: "Bilgili ve ilgili antrenörler; her seviyede güvenli ilerleme.",
  },
  {
    emoji: "❄️",
    title: "Yazın Klimalı",
    desc: "Sıcak havalarda ferah ve kontrollü iç ortam.",
  },
  {
    emoji: "📍",
    title: "Kolay Ulaşım",
    desc: "Atatürk Bulvarı üzerinde erişimi net bir konum.",
  },
  {
    emoji: "💰",
    title: "Uygun Fiyat",
    desc: "Kaliteli hizmet ve donanım için dengeli üyelik.",
  },
] as const;

export const REVIEWS = [
  {
    stars: 5,
    text:
      "Güzel ve bol ekipman var. 4 katlı olduğu için kalabalık olmuyor. Antrenörler ve sahipler çok ilgili ve bilgili. Çok temiz bir yer.",
    author: "Burak O.",
  },
  {
    stars: 4,
    text:
      "Döşemealtı'ndaki 3 spor salonuna da gittim. Fiyat-performans açısından iyi ve sıcakkanlılar. Ortam ortalamanın üzerinde.",
    author: "Faruk",
  },
  {
    stars: 5,
    text:
      "Ekipman çeşitliliği ve eğitmenlerin ilgisiyle bölgenin en iyi seçeneklerinden biri.",
    author: "Üye",
  },
] as const;

export const GALLERY = [
  { src: IMG.g1, hint: "Gym Floor", category: "Gym Floor · Salon" },
  { src: IMG.g2, hint: "Equipment", category: "Equipment · Ekipman" },
  { src: IMG.g3, hint: "Building Floors", category: "Building Floors · Katlar" },
  { src: IMG.g4, hint: "Gym Floor", category: "Gym Floor" },
  { src: IMG.g5, hint: "Equipment", category: "Equipment" },
  { src: IMG.g6, hint: "Building Floors", category: "Kat Planı" },
] as const;
