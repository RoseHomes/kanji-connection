import React, { Suspense, lazy, useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  ArrowUpRight,
  BookOpen,
  Sprout,
  Menu,
  X,
  Home as HomeIcon,
  GitCompareArrows,
  Library,
  CircleCheck,
} from "lucide-react";
import { LazyMotion, MotionConfig } from "motion/react";
import { Reveal } from "./ui";
import Home from "./pages/Home";
import "./styles.css";
import { AuthProvider, useAuth } from "./auth";
import { JAPANESE_AUDIO_ATTRIBUTION, LessonAudio } from "./lesson-audio";
const Catalog = lazy(() => import("./pages/Catalog"));
const Lesson = lazy(() => import("./pages/Lesson"));
const Explorer = lazy(() => import("./pages/Explorer"));
const KanjiDetail = lazy(() => import("./pages/KanjiDetail"));
const Compare = lazy(() => import("./pages/Compare"));
const Review = lazy(() => import("./pages/Review"));
const Account = lazy(() => import("./pages/Account"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Quiz = lazy(() => import("./pages/Quiz"));
const LearningPathList = lazy(() =>
  import("./pages/LearningPaths").then((m) => ({ default: m.LearningPathList })),
);
const LearningPathPage = lazy(() =>
  import("./pages/LearningPaths").then((m) => ({ default: m.LearningPathPage })),
);
const LearningUnitPage = lazy(() =>
  import("./pages/LearningPaths").then((m) => ({ default: m.LearningUnitPage })),
);
const client = new QueryClient({
  defaultOptions: { queries: { staleTime: 60000, retry: 1 } },
});
function App() {
  const { session } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname, search } = useLocation();
  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo(0, 0);
    document.getElementById("main")?.focus({ preventScroll: true });
    const labels: Record<string, string> = {
      lessons: "บทเรียน",
      categories: "เรียนตามหมวด",
      jlpt: "เตรียม JLPT",
      explore: "สำรวจคันจิ",
      compare: "เปรียบเทียบ",
      review: "ทบทวน",
      quiz: "แบบฝึกหัด",
      dashboard: "ความก้าวหน้า",
      account: "บัญชี",
    };
    document.title = `${labels[pathname.split("/")[1]] || "เรียนรู้คันจิ"} · Kanji Connection`;
  }, [pathname]);
  return (
    <>
      <a className="skip" href="#main">
        ข้ามไปยังเนื้อหา
      </a>
      <header
        className="site-header"
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setMenuOpen(false);
            document.getElementById("menu-toggle")?.focus();
          }
        }}
      >
        <Link className="brand" to="/">
          <span className="brand-mark" lang="ja">
            木
          </span>
          <span>
            kanji<span className="brand-light">connection</span>
            <small>ทุกตัวอักษร มีความเชื่อมโยง</small>
          </span>
        </Link>
        <button
          id="menu-toggle"
          className="menu-toggle"
          aria-label={menuOpen ? "ปิดเมนู" : "เปิดเมนู"}
          aria-controls="primary-navigation"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
        <nav
          id="primary-navigation"
          data-open={menuOpen}
          aria-label="เมนูหลัก"
          onClick={() => setMenuOpen(false)}
        >
          <NavLink to="/lessons">บทเรียน</NavLink>
          <NavLink to="/categories">เรียนตามหมวด</NavLink>
          <NavLink to="/jlpt">JLPT</NavLink>
          <NavLink to="/explore">สำรวจคันจิ</NavLink>
          <NavLink to="/compare">เปรียบเทียบ</NavLink>
          <NavLink to="/quiz">แบบฝึกหัด</NavLink>
          <span className="nav-divider" aria-hidden="true" />
          <NavLink to="/review">ทบทวน</NavLink>
          <NavLink to="/dashboard">ความก้าวหน้า</NavLink>
        </nav>
        <Link className="header-cta" to="/account">
          <BookOpen size={16} /> {session ? "บัญชี" : "เข้าสู่ระบบ"}{" "}
          <ArrowUpRight size={16} />
        </Link>
      </header>
      <main id="main" tabIndex={-1}>
        <Suspense
          fallback={
            <div className="page">
              <p role="status">กำลังเปิดหน้า…</p>
            </div>
          }
        >
          <Reveal key={pathname}>
            <LessonAudio enabled={!/^\/lessons\/[^/]+\/?$/.test(pathname)} playbackScope={`${pathname}${search}`}>
            <Routes key={session?.user.id || "guest"}>
              <Route path="/" element={<Home />} />
              <Route path="/lessons" element={<Catalog />} />
              <Route path="/lessons/:slug" element={<Lesson />} />
              <Route
                path="/categories"
                element={<LearningPathList kind="category" />}
              />
              <Route
                path="/categories/:slug"
                element={<LearningPathPage kind="category" />}
              />
              <Route
                path="/categories/:slug/units/:unitKey"
                element={<LearningUnitPage kind="category" />}
              />
              <Route path="/jlpt" element={<LearningPathList kind="jlpt" />} />
              <Route path="/jlpt/:slug" element={<LearningPathPage kind="jlpt" />} />
              <Route
                path="/jlpt/:slug/units/:unitKey"
                element={<LearningUnitPage kind="jlpt" />}
              />
              <Route path="/explore" element={<Explorer />} />
              <Route path="/explore/:character" element={<KanjiDetail />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/review" element={<Review />} />
              <Route path="/account" element={<Account />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/quiz" element={<Quiz />} />
              <Route path="/quiz/:slug" element={<Quiz />} />
              <Route
                path="*"
                element={
                  <div className="page section">
                    <h1>ไม่พบหน้านี้</h1>
                    <Link to="/">กลับหน้าแรก</Link>
                  </div>
                }
              />
            </Routes>
            </LessonAudio>
          </Reveal>
        </Suspense>
      </main>
      <nav className="mobile-nav" aria-label="เมนูมือถือ">
        {[
          { to: "/", label: "หน้าแรก", icon: HomeIcon },
          { to: "/lessons", label: "บทเรียน", icon: BookOpen },
          { to: "/compare", label: "เปรียบเทียบ", icon: GitCompareArrows },
          { to: "/quiz", label: "แบบฝึกหัด", icon: CircleCheck },
          { to: "/explore", label: "สำรวจ", icon: Library },
        ].map(({ to, label, icon: Icon }) => (
          <NavLink to={to} end={to === "/"} key={to}>
            <Icon size={17} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <footer>
        <Link to="/" className="footer-brand">
          <Sprout size={20} /> kanji connection
        </Link>
        <span>ค่อย ๆ เรียนรู้ วันละความเชื่อมโยง</span>
        <small className="footer-meta">
          <span>เรียนได้โดยไม่เข้าสู่ระบบ · All Rights Reserved</span>
          <span lang="ja">{JAPANESE_AUDIO_ATTRIBUTION}</span>
        </small>
      </footer>
    </>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <LazyMotion
        features={() => import("./motion-features").then((m) => m.default)}
      >
        <QueryClientProvider client={client}>
          <AuthProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </AuthProvider>
        </QueryClientProvider>
      </LazyMotion>
    </MotionConfig>
  </React.StrictMode>,
);
