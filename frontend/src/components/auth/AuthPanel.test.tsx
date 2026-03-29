import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AuthPanel from "@/components/auth/AuthPanel";

const mockUseAuth = vi.fn();

vi.mock("@/lib/auth", () => ({
  useAuth: () => mockUseAuth(),
}));

describe("AuthPanel", () => {
  it("renders the logged-out account access copy", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      notice: null,
      clearNotice: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<AuthPanel />);

    expect(screen.getByText("Account Access")).toBeInTheDocument();
    expect(
      screen.getByText("Use an account for protected features and future quotas. Mission planning will still attempt AI reranking when available."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  it("renders the authenticated state indicator", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "user-1",
        email: "demo.user@example.com",
        created_at: "2026-03-29T08:00:00Z",
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      notice: null,
      clearNotice: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<AuthPanel />);

    expect(screen.getByText("Session Active")).toBeInTheDocument();
    expect(screen.getByText("demo.user@example.com")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /logout/i })).toBeInTheDocument();
  });
});
