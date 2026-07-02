"use client";

import {
  BarChart3,
  Bookmark,
  History,
  LayoutDashboard,
  Radar,
  Search,
  Settings,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { useUiStore } from "@/store/ui";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/search", label: "Search", icon: Search },
  { href: "/candidates", label: "Candidates", icon: Users },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/history", label: "History", icon: History },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useUiStore((state) => state.sidebarCollapsed);

  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-screen shrink-0 border-r bg-card transition-[width] duration-200 md:flex md:flex-col",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <Link
        href="/dashboard"
        className="flex h-14 items-center gap-2 border-b px-4 text-primary"
      >
        <Radar className="h-6 w-6 shrink-0" />
        {!collapsed && (
          <span className="truncate text-sm font-semibold tracking-tight text-foreground">
            Talent Discovery
          </span>
        )}
      </Link>
      <nav className="flex-1 space-y-1 overflow-y-auto p-2 scrollbar-thin">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
                collapsed && "justify-center px-0",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>
      {!collapsed && (
        <p className="border-t p-3 text-[11px] leading-4 text-muted-foreground">
          Public-data sourcing only. Respects robots.txt &amp; site terms.
        </p>
      )}
    </aside>
  );
}
