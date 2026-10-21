// Siteye ait sabit bilgiler. İletişim bilgileri gerçektir (kullanıcı verdi). Sosyal medya adresleri hâlâ YER TUTUCUDUR.
// Başka hiçbir yerde iletişim bilgisi yazılmaz.
export const site = {
  name: 'Horpol Trailer Systems',
  // Konfigüratörde dorse plakasında yazan site adresi. ŞİMDİLİK yer tutucu (kullanıcı 2026-10-21: alan adı kesinleşince değişecek).
  plateText: 'horpol-trailer-systems',
  contact: {
    phone: '0 (536) 776 30 95',
    email: 'info@didebanotomotiv.com',
    address: {
      tr: 'Konuksever Mah. Gazi Bulv. No:256/A Muratpaşa Antalya',
      en: 'Konuksever Mah. Gazi Bulv. No:256/A, Muratpaşa, Antalya, Türkiye',
      ru: 'Конуксевер мах., бульвар Гази, № 256/А, Муратпаша, Анталья, Турция',
      ar: 'حي كونوكسيفير، شارع غازي، رقم 256/أ، مراد باشا، أنطاليا، تركيا',
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
