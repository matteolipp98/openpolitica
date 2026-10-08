// La home presenta i partiti come nel mock approvato (adr/mockup/vista-soggetti.html, #76).
import { expect, test } from "@playwright/test";

test("c'è l'emiciclo, e Camera e Senato si scambiano senza JavaScript", async ({ browser }) => {
  const contesto = await browser.newContext({ javaScriptEnabled: false });
  const page = await contesto.newPage();
  await page.goto("/");
  const camera = page.locator(".ramo-camera svg.emiciclo");
  const senato = page.locator(".ramo-senato svg.emiciclo");
  await expect(camera).toBeVisible();
  await expect(senato).toBeHidden();
  expect(await camera.locator("circle").count()).toBeGreaterThan(100);
  await page.locator("label[for=ramo-senato]").click();
  await expect(senato).toBeVisible();
  await expect(camera).toBeHidden();
  await contesto.close();
});

test("i pallini sono tanti quanti i parlamentari e la legenda torna", async ({ page }) => {
  await page.goto("/");
  const totale = Number((await page.locator(".ramo-camera .grande small").innerText()).match(/su ([\d.]+)/)![1]!.replace(".", ""));
  expect(await page.locator(".ramo-camera svg.emiciclo circle").count()).toBe(totale);
  const seggi = await page.locator(".ramo-camera .legenda li:not(.gruppo) .n").allInnerTexts();
  expect(seggi.map((s) => Number(s.replace(".", ""))).reduce((a, b) => a + b, 0)).toBe(totale);
});

test("le schede dei partiti sono in ordine alfabetico", async ({ page }) => {
  await page.goto("/");
  const nomi = await page.locator(".scheda .nome").allInnerTexts();
  expect(nomi.length).toBeGreaterThan(1);
  expect(nomi).toEqual([...nomi].sort((a, b) => a.localeCompare(b, "it")));
});

test("ogni scheda ha fonte e data, e le stesse domande per tutti", async ({ page }) => {
  await page.goto("/");
  const schede = page.locator(".scheda");
  const n = await schede.count();
  const prime = await schede.first().locator(".voti li > span:first-child").allInnerTexts();
  for (let i = 0; i < n; i++) {
    await expect(schede.nth(i).locator(".piede .fonte")).toContainText(/voti fino all?'? ?\d/);
    expect(await schede.nth(i).locator(".voti li > span:first-child").allInnerTexts()).toEqual(prime);
  }
});

test("nessuna frase sul partito che ha votato unito", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).not.toContainText(/votato unito/i);
});

test("dalle schede si arriva alle persone", async ({ page }) => {
  await page.goto("/");
  const link = page.locator(".scheda .chi a").first();
  const href = await link.getAttribute("href");
  expect(href).toMatch(/^\/persone\//);
  await link.click();
  await expect(page).toHaveURL(new RegExp(href!));
  await expect(page.locator("h1")).toBeVisible();
});
