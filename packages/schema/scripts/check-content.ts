import { caricaContenuti } from "./carica.js";
import { controllaRiferimenti, elencoDaVerificare } from "./controlli.js";

const { contenuti, errori } = caricaContenuti();
const tutti = [...errori, ...controllaRiferimenti(contenuti)];
const daVerificare = elencoDaVerificare(contenuti);

if (daVerificare.length) {
  console.log(`Da verificare sulle fonti (${daVerificare.length}):`);
  for (const d of daVerificare) console.log(`  - ${d}`);
}
if (tutti.length) {
  console.error(`\n${tutti.length} errori nei contenuti:`);
  for (const e of tutti) console.error(`  ${e.file}: ${e.messaggio}`);
  process.exit(1);
}
console.log("\nContenuti validi.");
