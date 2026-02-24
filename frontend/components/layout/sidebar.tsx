"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { BarChart2, Zap, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart2 },
  { href: "/analyze", label: "Analyze", icon: Zap },
  { href: "/history", label: "History", icon: Clock },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:flex flex-col w-56 shrink-0 border-r border-border/40 py-6 gap-1 px-3">
      {links.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link key={href} href={href}>
            <motion.div
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer",
                active
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              )}
              whileTap={{ scale: 0.98 }}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
              {active && (
                <motion.div
                  layoutId="sidebar-indicator"
                  className="ml-auto w-1.5 h-1.5 rounded-full bg-brand-blue"
                />
              )}
            </motion.div>
          </Link>
        );
      })}
    </aside>
  );
}
