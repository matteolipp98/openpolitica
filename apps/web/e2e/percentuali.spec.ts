// Nessuna percentuale senza il suo conteggio accanto (ADR 0019 e 0036, #58): "57%" va con "4 su 7".
// Vale per i numeri calcolati da noi: le frasi citate e i dati ufficiali con la loro fonte ("Ha detto / In realtà")
// stanno dentro [data-citazioni] e restano come sono.
import { readdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const OUT = path.resolve(import.meta.dirname, "../out");

// Tutte le pagine del sito costruito: out/partiti/x.html → /partiti/x
function pagine(dir = OUT): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((f) => {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) return f.name.startsWith("_") ? [] : pagine(p);
    if (!f.name.endsWith(".html") || f.name === "404.html" || f.name.startsWith("_")) return [];
    return ["/" + path.relative(OUT, p).replace(/\.html$/, "").replace(/(^|\/)index$/, "")];
  });
}

// Per ogni percentuale scritta, il blocco che la contiene: si sale finché c'è altro testo oltre al numero.
// Nel blocco ci deve essere un conteggio: "4 su 7", "su 3 di 10", "4 domande su 10".
async function percentualiNude(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const SOLO_NUMERO = /^\s*\d+(?:[.,]\d+)?\s*%\s*$/;
    const CONTEGGIO = /\d+\s+(?:\p{L}+\s+)?(?:su|di)\s+\d+/u;
    const nude: string[] = [];
    const giro = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = giro.nextNode(); n; n = giro.nextNode()) {
      if (!/\d\s*%/.test(n.textContent ?? "")) continue;
      let blocco = n.parentElement;
      if (!blocco || blocco.closest("script, style, [data-citazioni]")) continue;
      while (blocco.parentElement && SOLO_NUMERO.test(blocco.textContent ?? "")) blocco = blocco.parentElement;
      const testo = (blocco.textContent ?? "").replace(/\s+/g, " ").trim();
      if (!CONTEGGIO.test(testo)) nude.push(testo.slice(0, 160));
    }
    return nude;
  });
}

for (const url of pagine()) {
  test(`nessuna percentuale nuda in ${url}`, async ({ page }) => {
    await page.goto(url);
    expect(await percentualiNude(page)).toEqual([]);
  });
}

test("nessuna percentuale nuda nei risultati del questionario", async ({ page }) => {
  await page.goto("/domande");
  for (let i = 0; i < 50; i++) {
    const bottone = page.getByRole("button", { name: i % 3 ? "Sono contrario" : "Sono d'accordo" });
    if (!(await bottone.count())) break;
    await bottone.first().click();
  }
  await expect(page.getByText(/Il più vicino a te|Sono alla pari/)).toBeVisible();
  expect(await percentualiNude(page)).toEqual([]);
});

test("il controllo ferma una percentuale scritta da sola", async ({ page }) => {
  // Si aspetta che React abbia finito di attaccarsi alla pagina: prima, il paragrafo aggiunto verrebbe tolto
  await page.goto("/", { waitUntil: "networkidle" });
  await page.evaluate(() => {
    const p = document.createElement("p");
    p.textContent = "Il più vicino arriva solo al 40%.";
    document.querySelector("main")!.append(p);
  });
  expect(await percentualiNude(page)).toEqual(["Il più vicino arriva solo al 40%."]);
});
