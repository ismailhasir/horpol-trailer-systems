import { describe, expect, it } from "vitest";
import { axlePositions, sideMarkerPositions, stopLampPositions, trailerDims } from "./layout";

describe("layout", () => {
  it("yan markerları iki yana eşit böler ve dorse içinde tutar", () => {
    const length = 13.6;
    const { front, rear } = trailerDims(length);
    const pos = sideMarkerPositions(length, 8);
    expect(pos).toHaveLength(8);
    expect(pos.filter((p) => p[2] > 0)).toHaveLength(4);
    for (const [x] of pos) {
      expect(x).toBeGreaterThan(front);
      expect(x).toBeLessThan(rear);
    }
  });

  it("stop lambalarını arka uca simetrik yerleştirir", () => {
    const [a, b] = stopLampPositions(12, 2);
    expect(a[0]).toBeGreaterThanOrEqual(6);
    expect(a[2]).toBe(-b[2]);
  });

  it("kısa dorsede iki aks kullanır", () => {
    expect(axlePositions(9)).toHaveLength(2);
    expect(axlePositions(13.6)).toHaveLength(3);
  });
});
