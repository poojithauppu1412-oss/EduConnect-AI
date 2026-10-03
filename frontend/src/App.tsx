import { useEffect, useRef } from "react";
import OpportunityDetailPage from "./OpportunityDetailPage";
import OpportunitiesPage from "./OpportunitiesPage";
import ProfilePage from "./ProfilePage";
import { ClerkProvider, Show, SignIn, SignUp, useClerk, useUser } from "@clerk/react";
import { publishableKeyFromHost } from "@clerk/react/internal";
import { shadcn } from "@clerk/themes";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, BookOpen, BriefcaseBusiness, Compass, LogOut, Network, ShieldCheck } from "lucide-react";
import { Link, Redirect, Route, Router as WouterRouter, Switch, useLocation } from "wouter";

type ReadinessResponse = {
  status: string;
  database: string;
};

type AuthenticatedSession = {
  user_id: string;
  session_id: string | null;
};

const clerkPubKey = publishableKeyFromHost(
  window.location.hostname,
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY,
);
const clerkProxyUrl = import.meta.env.VITE_CLERK_PROXY_URL;
const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");

if (!clerkPubKey) {
  throw new Error("Missing VITE_CLERK_PUBLISHABLE_KEY.");
}

function stripBase(path: string): string {
  return basePath && path.startsWith(basePath)
    ? path.slice(basePath.length) || "/"
    : path;
}

const clerkAppearance = {
  theme: shadcn,
  options: {
    logoPlacement: "inside" as const,
    logoLinkUrl: basePath || "/",
    logoImageUrl: `${window.location.origin}${basePath}/logo.svg`,
  },
  variables: {
    colorPrimary: "#164c47",
    colorForeground: "#173b3a",
    colorMutedForeground: "#697b73",
    colorDanger: "#9e3d32",
    colorBackground: "#f5f3e9",
    colorInput: "#fffefa",
    colorInputForeground: "#173b3a",
    colorNeutral: "#d9ded0",
    fontFamily: '"DM Sans", ui-sans-serif, system-ui, sans-serif',
    borderRadius: "14px",
  },
  elements: {
    rootBox: { width: "100%", display: "flex", justifyContent: "center" },
    cardBox: {
      width: "min(440px, calc(100vw - 40px))",
      maxWidth: "100%",
      overflow: "hidden",
      borderRadius: "24px",
      border: "1px solid #d9ded0",
      backgroundColor: "#f5f3e9",
    },
    card: { boxShadow: "none", border: "0", backgroundColor: "transparent" },
    footer: { boxShadow: "none", border: "0", backgroundColor: "transparent" },
    headerTitle: { color: "#173b3a", fontFamily: "Manrope, sans-serif", fontWeight: 800 },
    headerSubtitle: { color: "#59716b" },
    socialButtonsBlockButtonText: { color: "#173b3a" },
    formFieldLabel: { color: "#173b3a", fontWeight: 600 },
    footerActionLink: { color: "#164c47", fontWeight: 700 },
    footerActionText: { color: "#59716b" },
    dividerText: { color: "#697b73" },
    identityPreviewEditButton: { color: "#164c47" },
    formFieldSuccessText: { color: "#164c47" },
    alertText: { color: "#7b3029" },
    logoBox: { borderRadius: "10px" },
    logoImage: { objectFit: "contain" },
    socialButtonsBlockButton: {
      borderColor: "#d9ded0",
      borderRadius: "12px",
      backgroundColor: "#fffefa",
    },
    formButtonPrimary: {
      borderRadius: "12px",
      backgroundColor: "#164c47",
      color: "#ffffff",
      fontWeight: 700,
    },
    formFieldInput: {
      borderColor: "#cbd4c7",
      borderRadius: "12px",
      backgroundColor: "#fffefa",
      color: "#173b3a",
    },
    footerAction: { color: "#59716b" },
    dividerLine: { backgroundColor: "#d9ded0" },
    alert: { borderRadius: "12px" },
    otpCodeFieldInput: { borderColor: "#cbd4c7", borderRadius: "10px" },
    formFieldRow: { marginBottom: "16px" },
    main: { gap: "18px" },
  },
};

async function checkReadiness(): Promise<ReadinessResponse> {
  const response = await fetch("/api/health/ready");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail?.database ?? "Service is not ready");
  }
  return payload as ReadinessResponse;
}

async function checkAuthenticatedSession(): Promise<AuthenticatedSession> {
  const response = await fetch("/api/auth/me", {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? "The API could not verify this session.");
  }
  return payload as AuthenticatedSession;
}

function Brand() {
  return (
    <Link className="brand" href="/" aria-label="EduConnect AI home">
      <span className="brand-mark" aria-hidden="true" />
      <span className="brand-name">
        EduConnect <span>AI</span>
      </span>
    </Link>
  );
}

function HomePage() {
  const readiness = useQuery({
    queryKey: ["service-readiness"],
    queryFn: checkReadiness,
    refetchInterval: 30_000,
  });
  const isChecking = readiness.isLoading || (!readiness.isError && !readiness.data);
  const readinessState = isChecking ? "loading" : readiness.isError ? "error" : "ready";
  const readinessMessage = isChecking
    ? "Checking API and PostgreSQL connection"
    : readiness.isError
      ? "API / PostgreSQL connection unavailable"
      : `API ${readiness.data?.status ?? "unknown"} · PostgreSQL ${readiness.data?.database ?? "unknown"}`;
  const readinessDetail = readiness.isError
    ? readiness.error instanceof Error
      ? readiness.error.message
      : "The readiness check could not be completed."
    : isChecking
      ? "The service check is in progress."
      : "Live readiness response from the application service";

  return (
    <div className="page-shell">
      <header className="site-header">
        <Brand />
        <div className="header-actions">
          <Link className="text-link" href="/sign-in">Sign in</Link>
          <Link className="primary-link" href="/sign-up">
            Create account <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </header>

      <main className="main-content">
        <section className="hero" aria-labelledby="welcome-title">
          <div className="hero-copy">
            <p className="eyebrow">Education, work &amp; what comes next</p>
            <h1 id="welcome-title">
              A clearer path to <em>what’s next.</em>
            </h1>
            <p className="hero-intro">
              Explore opportunities and find grounded guidance for your next
              move — wherever you are in your journey.
            </p>
            <div className="hero-actions">
              <Link className="primary-link hero-cta" href="/sign-up">
                Get started <ArrowUpRight size={17} aria-hidden="true" />
              </Link>
              <Link className="text-link" href="/sign-in">I already have an account</Link>
            </div>
          </div>

          <div
            className="hero-art"
            role="img"
            aria-label="A visual map connecting learning, work, and guidance"
          >
            <span className="art-kicker">Many directions. One starting point.</span>
            <div className="art-orbit" aria-hidden="true" />
            <div className="art-center" aria-hidden="true"><Network strokeWidth={1.4} /></div>
            <span className="orbit-node node-learning" aria-hidden="true"><BookOpen /></span>
            <span className="orbit-node node-work" aria-hidden="true"><BriefcaseBusiness /></span>
            <span className="orbit-node node-guidance" aria-hidden="true"><Compass /></span>
            <span className="orbit-label label-learning" aria-hidden="true">Learning</span>
            <span className="orbit-label label-work" aria-hidden="true">Work</span>
            <span className="orbit-label label-guidance" aria-hidden="true">Guidance</span>
            <div className="art-caption" aria-hidden="true">
              <span>Connected possibilities</span>
              <span>In development</span>
            </div>
          </div>
        </section>

        <section className="readiness-section" aria-labelledby="readiness-title">
          <div className="readiness-heading">
            <span className="readiness-symbol" aria-hidden="true"><ShieldCheck /></span>
            <div>
              <h2 id="readiness-title">Foundation check</h2>
              <p>The app checks its API and database connection in real time.</p>
            </div>
          </div>
          <div
            className="service-state"
            data-state={readinessState}
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            <div className="state-line">
              <span className="state-dot" aria-hidden="true" />
              <span>{readinessMessage}</span>
            </div>
            <p className="state-detail">{readinessDetail}</p>
          </div>
        </section>

        <section className="horizon" aria-labelledby="horizon-title">
          <h2 className="horizon-title" id="horizon-title">Built for the in-between moments.</h2>
          <div className="horizon-copy">
            <span className="horizon-rule" aria-hidden="true" />
            <p>
              Create an account to build your profile and browse verified
              opportunities when source-reviewed listings are available.
              Recommendations and guided assistance are still in development.
            </p>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <p>EduConnect AI · A thoughtful starting place for what’s next.</p>
        <span className="footer-stage">Phase 6 · Opportunity discovery</span>
      </footer>
    </div>
  );
}

function HomeRedirect() {
  return (
    <>
      <Show when="signed-in"><Redirect to="/dashboard" /></Show>
      <Show when="signed-out"><HomePage /></Show>
    </>
  );
}

function AccountPage() {
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  const session = useQuery({
    queryKey: ["auth-session", user?.id],
    queryFn: checkAuthenticatedSession,
    enabled: isLoaded && Boolean(user?.id),
  });

  return (
    <div className="page-shell account-shell">
      <header className="site-header">
        <Brand />
        <button className="secondary-link logout-button" type="button" onClick={() => signOut({ redirectUrl: basePath || "/" })}>
          <LogOut size={16} aria-hidden="true" /> Sign out
        </button>
      </header>
      <main className="account-main">
        <p className="eyebrow">Your EduConnect account</p>
        <h1>Welcome{user?.firstName ? `, ${user.firstName}` : ""}.</h1>
        <p className="account-intro">
          Your account is active. Browse source-reviewed opportunities or update
          your profile to keep your preferences current.
        </p>
        <section className="account-card" aria-labelledby="account-status-title">
          <div className="account-card-heading">
            <span className="readiness-symbol" aria-hidden="true"><ShieldCheck /></span>
            <div>
              <h2 id="account-status-title">Sign-in status</h2>
              <p>{user?.primaryEmailAddress?.emailAddress ?? "Authenticated with Clerk"}</p>
            </div>
          </div>
          <div className="service-state" data-state={session.isError ? "error" : session.isSuccess ? "ready" : "loading"} role="status" aria-live="polite">
            <div className="state-line">
              <span className="state-dot" aria-hidden="true" />
              <span>
                {session.isLoading
                  ? "Checking the API session"
                  : session.isError
                    ? "The API could not verify this session"
                    : "The API verified your Clerk session"}
              </span>
            </div>
            <p className="state-detail">
              {session.isError
                ? session.error instanceof Error ? session.error.message : "Try again after the service is available."
                : session.isSuccess
                  ? `Authenticated user ${session.data.user_id}`
                  : "A signed session cookie is checked by the FastAPI backend."}
            </p>
          </div>
        </section>
        <Link className="primary-link account-profile-link" href="/dashboard">
          Browse opportunities <ArrowUpRight size={15} aria-hidden="true" />
        </Link>
        <Link className="primary-link account-profile-link" href="/profile">
          View or edit your profile <ArrowUpRight size={15} aria-hidden="true" />
        </Link>
        <Link className="text-link account-home-link" href="/">Return to home <ArrowUpRight size={15} aria-hidden="true" /></Link>
      </main>
    </div>
  );
}

function SignInPage() {
  return (
    <main className="auth-screen">
      <div className="auth-panel">
        <div className="auth-context">
          <Brand />
          <p className="eyebrow">A connected next step</p>
        </div>
        <div className="auth-form-wrap">
          <SignIn routing="path" path={`${basePath}/sign-in`} signUpUrl={`${basePath}/sign-up`} />
        </div>
        <Link className="auth-home-link" href="/">Back to EduConnect AI</Link>
      </div>
    </main>
  );
}

function SignUpPage() {
  return (
    <main className="auth-screen">
      <div className="auth-panel">
        <div className="auth-context">
          <Brand />
          <p className="eyebrow">Your next step starts here</p>
        </div>
        <div className="auth-form-wrap">
          <SignUp routing="path" path={`${basePath}/sign-up`} signInUrl={`${basePath}/sign-in`} />
        </div>
        <Link className="auth-home-link" href="/">Back to EduConnect AI</Link>
      </div>
    </main>
  );
}

function ClerkQueryClientCacheInvalidator() {
  const { addListener } = useClerk();
  const queryClient = useQueryClient();
  const previousUserId = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    const unsubscribe = addListener(({ user }) => {
      const currentUserId = user?.id ?? null;
      if (previousUserId.current !== undefined && previousUserId.current !== currentUserId) {
        queryClient.clear();
      }
      previousUserId.current = currentUserId;
    });
    return unsubscribe;
  }, [addListener, queryClient]);

  return null;
}

function ClerkProviderWithRoutes() {
  const [, setLocation] = useLocation();

  return (
    <ClerkProvider
      publishableKey={clerkPubKey}
      proxyUrl={clerkProxyUrl}
      appearance={clerkAppearance}
      signInUrl={`${basePath}/sign-in`}
      signUpUrl={`${basePath}/sign-up`}
      localization={{
        signIn: { start: { title: "Welcome back", subtitle: "Sign in to continue" } },
        signUp: { start: { title: "Create your account", subtitle: "Get started with EduConnect AI" } },
      }}
      routerPush={(to) => setLocation(stripBase(to))}
      routerReplace={(to) => setLocation(stripBase(to), { replace: true })}
    >
      <ClerkQueryClientCacheInvalidator />
      <Switch>
        <Route path="/" component={HomeRedirect} />
        <Route path="/sign-in/*?" component={SignInPage} />
        <Route path="/sign-up/*?" component={SignUpPage} />
        <Route path="/account">
          <Show when="signed-in"><AccountPage /></Show>
          <Show when="signed-out"><Redirect to="/" /></Show>
        </Route>
        <Route path="/dashboard">
          <Show when="signed-in"><OpportunitiesPage /></Show>
          <Show when="signed-out"><Redirect to="/sign-in" /></Show>
        </Route>
        <Route path="/opportunities/:id">
          <Show when="signed-in"><OpportunityDetailPage /></Show>
          <Show when="signed-out"><Redirect to="/sign-in" /></Show>
        </Route>
        <Route path="/profile">
          <Show when="signed-in"><ProfilePage /></Show>
          <Show when="signed-out"><Redirect to="/sign-in" /></Show>
        </Route>
        <Route><Redirect to="/" /></Route>
      </Switch>
    </ClerkProvider>
  );
}

export default function App() {
  return (
    <WouterRouter base={basePath}>
      <ClerkProviderWithRoutes />
    </WouterRouter>
  );
}