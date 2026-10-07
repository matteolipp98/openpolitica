// Le risposte al questionario restano nel browser (ADR 0007, piano §9.4, #27).
import { expect, test, type Request } from "@playwright/test";

const BASE = "http://localhost:4310";

function registra(page: import("@playwright/test").Page): Request[] {
  const richieste: Request[] = [];
  page.on("request", (r) => richieste.push(r));
  return richieste;
}

test("rispondendo al questionario nessuna richiesta esce dal sito né porta le risposte", async ({ page }) => {
  const richieste = registra(page);
  await page.goto("/domande");
  const dopoCaricamento = richieste.length;

  // Si risponde a tutte le domande, segnando qualche "conta di più"
  for (let i = 0; i < 50; i++) {
    const bottone = page.getByRole("button", { name: i % 2 ? "Sono contrario" : "Sono d'accordo" });
    if (!(await bottone.count())) break;
    const casella = page.getByRole("checkbox");
    if (i % 3 === 0 && (await casella.count())) await casella.first().check();
    await bottone.first().click();
  }
  await expect(page.getByText("Il più vicino a te")).toBeVisible();

  // 1. nessuna richiesta verso altri siti, in tutta la sessione
  const fuori = richieste.filter((r) => !r.url().startsWith(BASE));
  expect(fuori.map((r) => r.url())).toEqual([]);
  // 2. rispondendo non parte nessuna richiesta che invia dati (niente POST, niente parametri)
  const durante = richieste.slice(dopoCaricamento);
  expect(durante.filter((r) => r.method() !== "GET").map((r) => `${r.method()} ${r.url()}`)).toEqual([]);
  // l'unico parametro ammesso è _rsc: il codice fisso del build che Next.js usa per precaricare le pagine
  const conParametri = durante.filter((r) => [...new URL(r.url()).searchParams.keys()].some((k) => k !== "_rsc"));
  expect(conParametri.map((r) => r.url())).toEqual([]);
  const codiciRsc = new Set(durante.map((r) => new URL(r.url()).searchParams.get("_rsc")).filter(Boolean));
  expect(codiciRsc.size).toBeLessThanOrEqual(1);
  // 3. le risposte stanno solo nel browser
  const salvato = await page.evaluate(() => localStorage.getItem("op.profilo.v1"));
  expect(salvato).not.toBeNull();
});

test("nessuna pagina chiede risorse ad altri siti", async ({ page }) => {
  const richieste = registra(page);
  for (const p of ["/", "/come-funziona", "/partiti/alleanza-progresso", "/persone/anna-pedretti"]) await page.goto(p);
  expect(richieste.filter((r) => !r.url().startsWith(BASE)).map((r) => r.url())).toEqual([]);
});
