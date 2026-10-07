import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Serif } from "next/font/google";
import Link from "next/link";
import "./globals.css";

// Font scaricati al build e serviti dal sito stesso: nessuna richiesta a Google da chi visita (ADR 0007, #27)
const sans = IBM_Plex_Sans({ weight: ["400", "500", "600"], subsets: ["latin"], variable: "--font-sans", display: "swap" });
const serif = IBM_Plex_Serif({ weight: ["600"], subsets: ["latin"], variable: "--font-serif", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Cosa hanno fatto davvero", template: "%s · openpolitica" },
  description: "Cosa dicono i politici, come votano in Parlamento, chi la pensa come te.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <div className="wrap">
          <nav className="menu" aria-label="Sezioni">
            <Link href="/">Partiti e persone</Link>
            <Link href="/domande">Chi la pensa come te</Link>
            <Link href="/come-funziona">Come funziona</Link>
          </nav>
          {children}
          <footer>
            Progetto indipendente. Il codice e il <Link href="/metodo">metodo</Link> sono pubblici. I dati vengono dai voti di Camera e Senato.
          </footer>
        </div>
      </body>
    </html>
  );
}
