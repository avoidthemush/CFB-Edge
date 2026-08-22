"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap, Target, TrendingUp, FileText, ListChecks, Menu, X } from "lucide-react";

const NAV_ITEMS = [
  { label: "Picks", href: "/", icon: Target },
  { label: "Form", href: "/recent-form", icon: TrendingUp },
  { label: "Sheet", href: "/bet-sheet", icon: FileText },
  { label: "Systems", href: "/systems", icon: ListChecks },
];

function NavLink({ item, active, onClick }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors border-l-2 ${
        active
          ? "bg-white/5 text-white border-[#ee6c4d]"
          : "text-white/60 border-transparent hover:bg-white/5 hover:text-white"
      }`}
    >
      <Icon size={18} />
      <span>{item.label}</span>
    </Link>
  );
}

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      <div className="md:hidden flex items-center justify-between bg-[#293241] text-white px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-[#ee6c4d]" />
          <span className="font-display font-bold text-lg tracking-wide">
            CFB EDGE
          </span>
        </div>
        <button onClick={() => setMobileOpen(true)} aria-label="Open menu">
          <Menu size={24} />
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="w-64 bg-[#293241] h-full p-4 flex flex-col">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2">
                <Zap size={20} className="text-[#ee6c4d]" />
                <span className="font-display font-bold text-lg text-white tracking-wide">
                  CFB EDGE
                </span>
              </div>
              <button onClick={() => setMobileOpen(false)} aria-label="Close menu">
                <X size={24} className="text-white" />
              </button>
            </div>
            <nav className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  active={pathname === item.href}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </nav>
          </div>
          <div className="flex-1 bg-black/60" onClick={() => setMobileOpen(false)} />
        </div>
      )}

      <aside className="hidden md:flex md:flex-col md:w-56 md:shrink-0 bg-[#293241] h-screen sticky top-0 p-4 border-r border-white/10">
        <div className="flex items-center gap-2 mb-10 mt-2 px-1">
          <Zap size={22} className="text-[#ee6c4d]" />
          <span className="font-display font-bold text-xl text-white tracking-wide">
            CFB EDGE
          </span>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.href} item={item} active={pathname === item.href} />
          ))}
        </nav>
      </aside>
    </>
  );
}