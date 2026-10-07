import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Cosa hanno fatto davvero", template: "%s · openpolitica" },
  description: "Cosa dicono i politici, come votano in Parlamento, chi la pensa come te.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@600&display=swap"
        />
      </head>
      <body>
        <div className="wrap">
          <nav className="menu" aria-label="Sezioni">
            <Link href="/">Partiti e persone</Link>
            <Link href="/domande">Chi la pensa come te</Link>
            <Link href="/nel-tempo">Nel tempo</Link>
            <Link href="/come-funziona">Come funziona</Link>
          </nav>
          {children}
          <footer>
            Progetto indipendente. Il codice e il metodo sono pubblici. I dati vengono dai voti di Camera e Senato.
          </footer>
        </div>
      </body>
    </html>
  );
}
