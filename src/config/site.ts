// Siteye ait sabit bilgiler. ÖNEMLİ: aşağıdaki iletişim bilgileri UYDURMA YER TUTUCUDUR (ADR-014).
// Yayından önce gerçek bilgilerle değiştirilmelidir. Başka hiçbir yerde iletişim bilgisi yazılmaz.
export const site = {
  name: 'Horpol Trailer Systems',
  contact: {
    phone: '+90 000 000 00 00',
    email: 'ornek@horpol.example',
    address: {
      tr: 'Örnek Mah. Örnek Cad. No: 0, Antalya, Türkiye',
      en: 'Example St. No: 0, Antalya, Türkiye',
      ru: 'ул. Пример, д. 0, Анталья, Турция',
      ar: 'شارع المثال رقم 0، أنطاليا، تركيا',
    },
  },
  // Sosyal medya bağlantıları: ŞİMDİLİK yer tutucu (platformların ana adresleri). Gerçek hesap adresleriyle değiştirilecek.
  social: {
    linkedin: 'https://www.linkedin.com/',
    facebook: 'https://www.facebook.com/',
    x: 'https://x.com/',
    instagram: 'https://www.instagram.com/',
  },
} as const;
