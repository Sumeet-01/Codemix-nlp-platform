"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Clock, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart2 },
  { href: "/analyze", label: "Analyze", icon: Zap },
  { href: "/history", label: "History", icon: Clock },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex h-14 items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-blue to-purple-500 flex items-center justify-center">
            <span className="text-white text-xs font-bold">CM</span>
          </div>
          <span className="font-semibold text-sm hidden sm:block">CodeMix NLP</span>
        </Link>

        {/* Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href}>
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  "gap-2 text-muted-foreground",
                  pathname === href && "text-foreground bg-secondary"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </Button>
            </Link>
          ))}
        </nav>

        {/* Right side — branding only */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground hidden sm:block">NLP Project</span>
        </div>
      </div>
    </header>
  );
}
