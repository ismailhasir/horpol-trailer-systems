// Sepet ve konfigüratör PDF'lerinin ortak parçaları. Bağımlılık yoktur: sayfalar canvas'ta çizilip JPEG'e çevrilir,
// bu dosya JPEG'leri minimal bir PDF'e (sayfa başına bir tam sayfa görüntü) koyar.

export const loadImg = (src: string) =>
  new Promise<HTMLImageElement | null>((res) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = () => res(null);
    i.src = src;
  });

/** Her JPEG bir A4 sayfa olan PDF (w, h: JPEG piksel boyutu) */
export function pdfFromJpegs(jpegs: Uint8Array[], w: number, h: number): Blob {
  const enc = new TextEncoder();
  const parts: Uint8Array[] = [];
  const offsets: number[] = [];
  let pos = 0;
  const push = (d: Uint8Array | string) => {
    const b = typeof d === 'string' ? enc.encode(d) : d;
    parts.push(b);
    pos += b.length;
  };
  const obj = (n: number, body: string | (() => void)) => {
    offsets[n] = pos;
    push(`${n} 0 obj\n`);
    typeof body === 'string' ? push(body) : body();
    push('\nendobj\n');
  };
  const PW = 595.28;
  const PH = 841.89;
  const n = jpegs.length;
  // nesneler: 1 katalog, 2 sayfa ağacı, sonra her sayfa için (sayfa, içerik, görüntü)
  const pageObj = (i: number) => 3 + i * 3;
  push('%PDF-1.4\n');
  obj(1, '<< /Type /Catalog /Pages 2 0 R >>');
  obj(2, `<< /Type /Pages /Kids [${jpegs.map((_, i) => `${pageObj(i)} 0 R`).join(' ')}] /Count ${n} >>`);
  jpegs.forEach((jpeg, i) => {
    const p = pageObj(i);
    obj(p, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PW} ${PH}] /Contents ${p + 1} 0 R /Resources << /XObject << /Im0 ${p + 2} 0 R >> >> >>`);
    const content = `q ${PW} 0 0 ${PH} 0 0 cm /Im0 Do Q`;
    obj(p + 1, `<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
    obj(p + 2, () => {
      push(`<< /Type /XObject /Subtype /Image /Width ${w} /Height ${h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`);
      push(jpeg);
      push('\nendstream');
    });
  });
  const total = 3 + n * 3;
  const xref = pos;
  push(`xref\n0 ${total}\n0000000000 65535 f \n`);
  for (let i = 1; i < total; i++) push(`${String(offsets[i]).padStart(10, '0')} 00000 n \n`);
  push(`trailer\n<< /Size ${total} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`);
  return new Blob(parts as BlobPart[], { type: 'application/pdf' });
}

export function saveBlob(blob: Blob, name: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
