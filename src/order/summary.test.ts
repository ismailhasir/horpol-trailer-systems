import { describe, expect, it } from "vitest";
import { defaultConfiguration } from "../state/config";
import { summaryText } from "./summary";

describe("summaryText", () => {
  it("varsayılan seçimi proje şemasındaki biçimde yazar", () => {
    expect(summaryText(defaultConfiguration())).toBe(
      [
        "Sipariş özeti",
        "Dorse tipi: Standart Dorse",
        "Soket: 7x2",
        "Set uzunluğu: 13,60 mt",
        "Stop: 2 × LZD 3049/H101/AMP1",
        "Yan marker: 8 × LD 2774",
        "Plaka: 2 × LTD 2834",
      ].join("\n"),
    );
  });

  it("adedi sıfır olan lamba kategorisini atlar", () => {
    const config = defaultConfiguration();
    config.lamps.plate.count = 0;
    expect(summaryText(config)).not.toContain("Plaka");
  });
});
