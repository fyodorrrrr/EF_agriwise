import { FloatingChat } from "./FloatingChat";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <Sidebar />
      <div className="shell-content">
        <main id="main-content" tabIndex={-1} className="shell-main">
          {children}
        </main>
      </div>
      <FloatingChat />
    </div>
  );
}
