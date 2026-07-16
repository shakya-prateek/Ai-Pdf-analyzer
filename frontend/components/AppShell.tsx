"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  BrandIcon,
  FileIcon,
  FilesIcon,
  MessageIcon,
  SearchIcon,
  UploadIcon
} from "./Icons";

const navItems = [
  { label: "New", href: "/", icon: UploadIcon },
  { label: "Documents", href: "/documents", icon: FilesIcon },
  { label: "Investigator", href: "/investigator", icon: SearchIcon },
  { label: "Chats", href: "/chats", icon: MessageIcon },
  { label: "Humanizer", href: "/humanizer", icon: BrandIcon },
  { label: "Paraphraser", href: "/paraphraser", icon: FileIcon },
  { label: "Study", href: "/study", icon: FilesIcon },
  { label: "Images", href: "/images", icon: UploadIcon }
];

function isActive(pathname: string, href: string) {
  if (href === "/documents") return pathname === "/documents" || pathname === "/upload";
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="res-app">
      <aside className="res-sidebar" aria-label="Primary navigation">
        <div className="res-sidebar__top">
          <Link href="/" className="res-logo" aria-label="PDF Analyzer home">
            <span><BrandIcon className="h-6 w-6" /></span>
          </Link>
          <button type="button" className="res-collapse" aria-label="Collapse sidebar">
            <span />
            <span />
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
          <button type="button" className="res-theme">
            <span aria-hidden="true">Aa</span>
            Dark theme
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
            <strong>PDF Analyzer</strong>
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
