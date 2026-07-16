"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandIcon, FilesIcon, MessageIcon } from "./Icons";

const navigation = [
  { href: "/", label: "Ask documents", icon: MessageIcon },
  { href: "/upload", label: "Document library", icon: FilesIcon }
];

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <Link href="/" className="brand" aria-label="DocuScope home">
          <span className="brand__mark"><BrandIcon className="h-5 w-5" /></span>
          <span>
            <strong>PDF Analyzer</strong>
            <small>Evidence workspace</small>
          </span>
        </Link>
        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map(({ href, label, icon: NavIcon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={active ? "primary-nav__item primary-nav__item--active" : "primary-nav__item"}
                aria-current={active ? "page" : undefined}
              >
                <NavIcon className="h-4 w-4" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="header-status" title="Files stay on this local application">
          <span className="status-dot" />
          Local workspace
        </div>
      </div>
    </header>
  );
}
