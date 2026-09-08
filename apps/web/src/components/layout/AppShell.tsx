import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <Sidebar />
      <div className="shell-content">
        <main className="shell-main">{children}</main>
      </div>
    </div>
  );
}
