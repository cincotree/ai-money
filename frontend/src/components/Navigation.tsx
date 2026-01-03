"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="bg-gray-800 p-3">
      <div className="flex gap-8">
        <Link
          href="/"
          className={`text-xl font-bold ${pathname === "/" ? "text-white" : "text-gray-400 hover:text-white"
            }`}
        >
          🤖 AI Money
        </Link>
        <Link
          href="/networth"
          className={`text-xl font-bold ${pathname === "/networth" ? "text-white" : "text-gray-400 hover:text-white"
            }`}
        >
          💰 Net Worth
        </Link>
      </div>
    </nav>
  );
}
