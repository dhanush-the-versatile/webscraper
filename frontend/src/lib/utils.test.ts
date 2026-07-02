import { describe, expect, it } from "vitest";

import { cn, initials, labelForAction, scoreTone } from "@/lib/utils";

describe("cn", () => {
  it("merges tailwind classes with later overrides winning", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-sm", false && "hidden", "font-bold")).toBe("text-sm font-bold");
  });
});

describe("initials", () => {
  it("takes the first letters of up to two words", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("Plato")).toBe("P");
    expect(initials("Anne Marie van Dijk")).toBe("AM");
  });
  it("falls back for empty values", () => {
    expect(initials(null)).toBe("?");
    expect(initials("")).toBe("?");
  });
});

describe("scoreTone", () => {
  it("maps score bands to tones", () => {
    expect(scoreTone(90)).toContain("emerald");
    expect(scoreTone(70)).toContain("sky");
    expect(scoreTone(50)).toContain("amber");
    expect(scoreTone(10)).toContain("rose");
  });
});

describe("labelForAction", () => {
  it("humanizes known actions and passes unknown through", () => {
    expect(labelForAction("search.created")).toBe("Started a search");
    expect(labelForAction("custom.thing")).toBe("custom.thing");
  });
});
