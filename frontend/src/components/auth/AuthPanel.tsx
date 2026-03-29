import { useState } from "react";
import { Loader2, LockKeyhole, LogOut, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  GENERIC_RETRY_MESSAGE,
  INVALID_INPUT_MESSAGE,
  isApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const AuthPanel = () => {
  const { user, isAuthenticated, isLoading, notice, clearNotice, login, register, logout } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    const normalizedEmail = email.trim();
    const normalizedPassword = password.trim();

    if (!normalizedEmail || !normalizedPassword) {
      setFormMessage(INVALID_INPUT_MESSAGE);
      return;
    }

    setIsSubmitting(true);
    setFormMessage(null);
    clearNotice();

    try {
      if (mode === "login") {
        const authenticatedUser = await login({
          email: normalizedEmail,
          password: normalizedPassword,
        });
        toast.success("Logged in", {
          description: `${authenticatedUser.email} now has an active session for protected features.`,
        });
      } else {
        const authenticatedUser = await register({
          email: normalizedEmail,
          password: normalizedPassword,
        });
        toast.success("Account created", {
          description: `${authenticatedUser.email} is ready to use.`,
        });
      }
      setPassword("");
    } catch (error) {
      const message = isApiError(error) ? error.message : GENERIC_RETRY_MESSAGE;
      setFormMessage(message);
      toast.error(mode === "login" ? "Login failed" : "Register failed", {
        description: message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setIsSubmitting(true);
    setFormMessage(null);

    try {
      await logout();
      toast.success("Logged out", {
        description: "Protected account access has been cleared for this browser session.",
      });
    } catch {
      setFormMessage(GENERIC_RETRY_MESSAGE);
      toast.error("Logout failed", {
        description: GENERIC_RETRY_MESSAGE,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isAuthenticated && user) {
    return (
      <div className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/8 p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-2 rounded border border-neon-cyan/35 bg-neon-cyan/10 px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-neon-cyan">
              <Sparkles className="h-3.5 w-3.5" />
              Session Active
            </div>
            <p className="text-sm font-semibold text-foreground">{user.email}</p>
            <p className="text-xs text-foreground/70">
              Authenticated sessions protect account features and future quotas while keeping credentials in an HTTP-only cookie.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={handleLogout}
            disabled={isSubmitting}
            className="border-glass-border bg-muted/20 text-foreground hover:bg-muted/40"
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogOut className="mr-2 h-4 w-4" />}
            Logout
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-glass-border bg-black/10 p-3">
      <div className="mb-3 flex items-start gap-2">
        <LockKeyhole className="mt-0.5 h-4 w-4 text-neon-cyan" />
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.24em] text-muted-foreground">
            Account Access
          </p>
          <p className="mt-1 text-xs text-foreground/70">
            Use an account for protected features and future quotas. Mission planning will still attempt AI reranking when available.
          </p>
        </div>
      </div>

      <Tabs
        value={mode}
        onValueChange={(value) => {
          setMode(value === "register" ? "register" : "login");
          setFormMessage(null);
          clearNotice();
        }}
      >
        <TabsList className="grid h-9 w-full grid-cols-2 bg-muted/20">
          <TabsTrigger value="login">Login</TabsTrigger>
          <TabsTrigger value="register">Register</TabsTrigger>
        </TabsList>

        <TabsContent value="login" className="space-y-3">
          <div className="space-y-2">
            <Input
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setFormMessage(null);
              }}
              autoComplete="email"
              placeholder="Email"
              className="border-glass-border bg-muted/20"
            />
            <Input
              type="password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setFormMessage(null);
              }}
              autoComplete="current-password"
              placeholder="Password"
              className="border-glass-border bg-muted/20"
            />
          </div>
        </TabsContent>

        <TabsContent value="register" className="space-y-3">
          <div className="space-y-2">
            <Input
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setFormMessage(null);
              }}
              autoComplete="email"
              placeholder="Email"
              className="border-glass-border bg-muted/20"
            />
            <Input
              type="password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setFormMessage(null);
              }}
              autoComplete="new-password"
              placeholder="Password (8+ characters)"
              className="border-glass-border bg-muted/20"
            />
          </div>
        </TabsContent>
      </Tabs>

      {(notice || formMessage) && (
        <div className="mt-3 rounded border border-neon-orange/30 bg-neon-orange/8 px-3 py-2 text-xs text-foreground/80">
          {formMessage || notice}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-[11px] text-muted-foreground">
          {isLoading ? "Checking session..." : "Session protection uses a server-side cookie."}
        </p>
        <Button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting || isLoading}
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {mode === "login" ? "Login" : "Create account"}
        </Button>
      </div>
    </div>
  );
};

export default AuthPanel;
