"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  BrandIcon,
  FileIcon,
  FilesIcon,
  MessageIcon,
  SearchIcon,
  UploadIcon
} from "./Icons";

const navItems = [
  { label: "New", href: "/workspace", icon: UploadIcon },
  { label: "Documents", href: "/documents", icon: FilesIcon },
  { label: "Investigator", href: "/investigator", icon: SearchIcon },
  { label: "Chats", href: "/chats", icon: MessageIcon },
  { label: "Humanizer", href: "/humanizer", icon: BrandIcon },
  { label: "Paraphraser", href: "/paraphraser", icon: FileIcon },
  { label: "Study", href: "/study", icon: FilesIcon },
  { label: "Healthcare", href: "/healthcare", icon: BrandIcon },
  { label: "Images", href: "/images", icon: UploadIcon }
];

function isActive(pathname: string, href: string) {
  if (href === "/documents") return pathname === "/documents" || pathname === "/upload";
  if (href === "/workspace") return pathname === "/workspace";
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkTheme, setDarkTheme] = useState(false);

  useEffect(() => {
    try {
      setDarkTheme(window.localStorage.getItem("askmypdf-theme") === "dark");
    } catch {
      setDarkTheme(false);
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("askmypdf-theme", darkTheme ? "dark" : "light");
    } catch {
      // Theme persistence is optional; keep the visual toggle working.
    }
  }, [darkTheme]);

  if (pathname === "/") {
    return <>{children}</>;
  }
  return (
    <div
      className={[
        "res-app",
        sidebarOpen ? "" : "res-app--collapsed",
        darkTheme ? "theme-dark" : ""
      ].filter(Boolean).join(" ")}
    >
      <aside className="res-sidebar" aria-label="Primary navigation">
        <div className="res-sidebar__top">
          <Link href="/" className="res-logo" aria-label="AskMyPDF AI home">
            <span><BrandIcon className="h-6 w-6" /></span>
          </Link>
          <button
            type="button"
            className="res-collapse"
            aria-label={sidebarOpen ? "Collapse sidebar" : "Open sidebar"}
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen((current) => !current)}
            title={sidebarOpen ? "Collapse sidebar" : "Open sidebar"}
          >
            <span className="res-collapse__panel" aria-hidden="true">
              <span className="res-collapse__pane res-collapse__pane--left" />
              <span className="res-collapse__pane res-collapse__pane--right" />
            </span>
          </button>
        </div>

        <nav className="res-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={isActive(pathname, item.href) ? "res-nav__item res-nav__item--active" : "res-nav__item"}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="res-sidebar__bottom">
          <button
            type="button"
            className={darkTheme ? "res-theme res-theme--active" : "res-theme"}
            aria-pressed={darkTheme}
            onClick={() => setDarkTheme((current) => !current)}
          >
            <span aria-hidden="true">Aa</span>
            {darkTheme ? "Light theme" : "Dark theme"}
          </button>
          <div className="res-local">
            <strong>Local workspace</strong>
            <span>No login required</span>
          </div>
        </div>
      </aside>

      <main className="res-main">
        <header className="res-topbar">
          <div>
            <strong>AskMyPDF AI</strong>
            <span>AI workspace for documents, writing, and study</span>
          </div>
          <Link href="/documents" className="res-create">
            <UploadIcon className="h-4 w-4" />
            Upload PDF
          </Link>
        </header>
        {children}
      </main>
    </div>
  );
}
