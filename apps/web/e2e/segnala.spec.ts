// "Hai trovato un errore?" (#26): il modulo chiama public.segnala su Supabase. Qui Supabase è finto.
import { expect, test } from "@playwright/test";

test.skip(!process.env.NEXT_PUBLIC_SUPABASE_URL, "build senza Supabase: il modulo non si mostra");

test("una segnalazione arriva alla funzione segnala con la pagina e il testo", async ({ page }) => {
  let corpo: Record<string, string> | null = null;
  await page.route(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/**`, async (route) => {
    corpo = route.request().postDataJSON();
    expect(route.request().url()).toMatch(/\/rest\/v1\/rpc\/segnala$/);
    await route.fulfill({ status: 200, contentType: "application/json", body: '{"ok":true}' });
  });
  await page.goto("/partiti/alleanza-progresso");
  await page.getByRole("button", { name: /Hai trovato un errore/ }).click();
  await page.getByLabel("Cosa non va?").fill("Il voto sul salario minimo è del 2023, non del 2024.");
  await page.getByRole("button", { name: "Invia la segnalazione" }).click();
  await expect(page.getByText(/Grazie\. Ricontrolliamo/)).toBeVisible();
  expect(corpo).toMatchObject({ p_url: "/partiti/alleanza-progresso", p_trappola: "" });
  expect(corpo!.p_testo).toContain("salario minimo");
});

test("troppe segnalazioni: il messaggio lo dice in parole semplici", async ({ page }) => {
  await page.route(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/**`, (route) =>
    route.fulfill({ status: 400, contentType: "application/json", body: '{"message":"troppe segnalazioni, riprova tra un\'ora"}' }),
  );
  await page.goto("/metodo");
  await page.getByRole("button", { name: /Hai trovato un errore/ }).click();
  await page.getByLabel("Cosa non va?").fill("Manca una correzione che avevate promesso.");
  await page.getByRole("button", { name: "Invia la segnalazione" }).click();
  await expect(page.getByText("Hai mandato troppe segnalazioni di seguito. Riprova tra un'ora.")).toBeVisible();
});
