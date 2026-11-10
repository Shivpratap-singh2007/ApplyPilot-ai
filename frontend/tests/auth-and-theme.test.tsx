import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { AuthProvider } from "@/components/providers/AuthProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import LandingPage from "@/app/page";
import LoginPage from "@/app/login/page";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}));

describe("ApplyPilot AI Phase 1 Frontend", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    pushMock.mockReset();
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("renders landing page core value propositions", () => {
    render(<LandingPage />);
    expect(
      screen.getByRole("heading", { name: /apply faster without giving up accuracy or control/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/100% local ai inference/i)).toBeInTheDocument();
    expect(screen.getByText(/human approval gate/i)).toBeInTheDocument();
  });

  it("toggles dark and light theme and persists preference", () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    );

    const toggle = screen.getByRole("button", { name: /switch to dark theme/i });
    fireEvent.click(toggle);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(window.localStorage.getItem("applypilot-theme")).toBe("dark");
  });

  it("submits login form and surfaces backend error messages", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Not authenticated" }), { status: 401 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Invalid email or password." }), { status: 401 })
      );

    render(
      <ThemeProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </ThemeProvider>
    );

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "ada@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "WrongPassword123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password.");
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
