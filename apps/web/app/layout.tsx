import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";

// Font nel repository (app/fonts, licenza OFL) e serviti dal sito stesso: la build non scarica nulla
// e nessuna richiesta a Google da chi visita (ADR 0007, #27, #72)
const sans = localFont({
  src: [
    { path: "./fonts/ibm-plex-sans-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/ibm-plex-sans-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/ibm-plex-sans-latin-600-normal.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-sans",
  display: "swap",
});
const serif = localFont({
  src: [{ path: "./fonts/ibm-plex-serif-latin-600-normal.woff2", weight: "600", style: "normal" }],
  variable: "--font-serif",
  display: "swap",
});

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
            <Link href="/">Partiti</Link>
            <Link href="/domande">Chi la pensa come te</Link>
            <Link href="/come-funziona">Come funziona</Link>
          </nav>
          {children}
          <footer>
            Progetto indipendente. Il codice e il <Link href="/metodo">metodo</Link> sono pubblici. I dati vengono dai voti di Camera e Senato e dai programmi elettorali depositati al Ministero dell&apos;Interno.
          </footer>
        </div>
      </body>
    </html>
  );
}
