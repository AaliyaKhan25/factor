"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Icon, { type IconName } from "@/components/ui/Icon";

type NavItem = { href: string; label: string; icon: IconName; count?: string };
const groups: { label: string; items: NavItem[] }[] = [
  { label: "WORKSPACE", items: [{ href: "/dashboard", label: "Overview", icon: "grid" }, { href: "/inbox", label: "Inbox", icon: "inbox", count: "4" }, { href: "/orders", label: "Orders", icon: "package" }, { href: "/catalog", label: "Catalog", icon: "box" }, { href: "/customers", label: "Customers", icon: "users" }] },
  { label: "OPERATIONS", items: [{ href: "/assets", label: "Assets", icon: "box" }, { href: "/allocations", label: "Allocations", icon: "arrow" }, { href: "/bookings", label: "Bookings", icon: "calendar" }, { href: "/payments", label: "Payments", icon: "wallet", count: "2" }, { href: "/cases", label: "Cases & returns", icon: "clock" }] },
  { label: "INSIGHTS", items: [{ href: "/reports", label: "Reports", icon: "chart" }, { href: "/activity", label: "Activity log", icon: "trend" }] },
  { label: "MANAGE", items: [{ href: "/transfers", label: "Transfers", icon: "arrow" }, { href: "/audits", label: "Audits", icon: "check" }, { href: "/setup/team", label: "Team", icon: "users" }, { href: "/setup/categories", label: "Categories", icon: "box" }, { href: "/setup/departments", label: "Departments", icon: "grid" }, { href: "/notifications", label: "Notifications", icon: "bell" }] },
];
const mobileItems = [groups[0].items[0], groups[0].items[1], groups[0].items[2], groups[1].items[0], groups[1].items[3]];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pageLabel = groups.flatMap((g) => g.items).find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.label ?? "Workspace";
  const links = (mobile = false) => (mobile ? mobileItems : groups.flatMap((group) => group.items)).map((item) => {
    const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
    return <Link key={item.href} href={item.href} onClick={() => setDrawerOpen(false)} className={`nav-link ${active ? "nav-link-active" : ""} ${mobile ? "mobile-nav-link" : ""}`}><span className="nav-icon"><Icon name={item.icon as IconName} size={19} /></span><span>{mobile ? item.label === "Overview" ? "Home" : item.label : item.label}</span>{item.count && !mobile && <span className="nav-count">{item.count}</span>}</Link>;
  });

  return <div className="app-frame">
    <aside className="sidebar">
      <Link href="/dashboard" className="brand-lockup"><span className="brand-mark">f</span><span className="brand-name">factor<span className="brand-period">.</span></span></Link>
      <button className="business-switcher"><span className="business-avatar">S</span><span className="business-name-wrap"><strong>Studio Aarna</strong><small>Owner workspace</small></span><span className="switch-chevron">⌄</span></button>
      <Link href="/orders/new" className="sidebar-create"><Icon name="plus" size={18} /> Create order <span>⌘ K</span></Link>
      <nav className="sidebar-nav">{groups.map((group) => <div className="nav-group" key={group.label}><p className="nav-group-label">{group.label}</p>{group.items.map((item) => {
        const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
        return <Link key={item.href} href={item.href} className={`nav-link ${active ? "nav-link-active" : ""}`}><span className="nav-icon"><Icon name={item.icon as IconName} size={19} /></span><span>{item.label}</span>{item.count && <span className="nav-count">{item.count}</span>}</Link>;
      })}</div>)}</nav>
      <div className="sidebar-bottom"><div className="plan-card"><span className="plan-spark"><Icon name="spark" size={17} /></span><strong>Make every day flow.</strong><p>Your business, all in one place.</p><Link href="/reports">Explore insights <Icon name="arrow" size={14} /></Link></div><Link href="/settings" className={`nav-link ${pathname.startsWith("/settings") ? "nav-link-active" : ""}`}><span className="nav-icon"><Icon name="settings" size={19} /></span><span>Settings</span></Link><div className="account-chip"><div className="account-avatar">RK</div><span><strong>Riya Kapoor</strong><small>Business owner</small></span><span className="account-more">•••</span></div></div>
    </aside>
    {drawerOpen && <button className="drawer-scrim" aria-label="Close navigation" onClick={() => setDrawerOpen(false)} />}
    <div className={`mobile-drawer ${drawerOpen ? "mobile-drawer-open" : ""}`}><div className="drawer-head"><Link href="/dashboard" className="brand-lockup"><span className="brand-mark">f</span><span className="brand-name">factor<span className="brand-period">.</span></span></Link><button className="icon-button" onClick={() => setDrawerOpen(false)} aria-label="Close"><Icon name="close" /></button></div><button className="business-switcher"><span className="business-avatar">S</span><span className="business-name-wrap"><strong>Studio Aarna</strong><small>Owner workspace</small></span><span className="switch-chevron">⌄</span></button><nav className="sidebar-nav">{groups.map((group) => <div className="nav-group" key={group.label}><p className="nav-group-label">{group.label}</p>{group.items.map((item) => { const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`)); return <Link key={item.href} href={item.href} onClick={() => setDrawerOpen(false)} className={`nav-link ${active ? "nav-link-active" : ""}`}><span className="nav-icon"><Icon name={item.icon as IconName} size={19} /></span><span>{item.label}</span></Link>; })}</div>)}<Link href="/settings" className="nav-link"><span className="nav-icon"><Icon name="settings" size={19} /></span><span>Settings</span></Link></nav></div>
    <div className="app-column"><header className="topbar"><div className="topbar-left"><button className="icon-button menu-button" onClick={() => setDrawerOpen(true)} aria-label="Open navigation"><Icon name="menu" /></button><div className="breadcrumbs"><span>Workspace</span><Icon name="chevron" size={14} /><strong>{pageLabel}</strong></div></div><div className="topbar-actions"><label className="global-search"><Icon name="search" size={18} /><input aria-label="Search" placeholder="Search anything..." /><kbd>⌘ K</kbd></label><Link href="/notifications" className="icon-button notification-button" aria-label="Notifications"><Icon name="bell" size={19} /><i /></Link><div className="topbar-divider" /><button className="topbar-profile"><span className="account-avatar">RK</span><span>Riya Kapoor</span><span className="switch-chevron">⌄</span></button></div></header><main className="main-content">{children}</main><footer className="app-footer"><span>Made for the way you do business.</span><span>Help center <b>·</b> Privacy <b>·</b> English (IN)</span></footer></div>
    <nav className="mobile-tabbar" aria-label="Main navigation">{links(true)}<button className="mobile-nav-link mobile-menu-link" onClick={() => setDrawerOpen(true)}><span className="nav-icon"><Icon name="menu" size={19} /></span><span>More</span></button></nav>
  </div>;
}
