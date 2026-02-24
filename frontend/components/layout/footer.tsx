import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border/40 py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-brand-blue to-purple-500 flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">CM</span>
          </div>
          <span className="text-sm font-medium">CodeMix NLP</span>
        </div>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} CodeMix NLP — Indian multilingual text intelligence
        </p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <Link href="/analyze" className="hover:text-foreground transition-colors">Analyze</Link>
          <Link href="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link>
        </div>
      </div>
    </footer>
  );
}
