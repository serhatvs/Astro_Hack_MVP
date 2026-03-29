import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  GENERIC_RETRY_MESSAGE,
  LOGIN_REQUIRED_MESSAGE,
  SESSION_EXPIRED_MESSAGE,
  fetchCurrentUser,
  isApiError,
  loginUser,
  logoutUser,
  registerUser,
} from "@/lib/api";
import type { AuthPayload, AuthUser } from "@/lib/types";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  notice: string | null;
  clearNotice: () => void;
  login: (payload: AuthPayload) => Promise<AuthUser>;
  register: (payload: AuthPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
}

const defaultContext: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  notice: null,
  clearNotice: () => undefined,
  login: async () => {
    throw new Error("Auth provider unavailable");
  },
  register: async () => {
    throw new Error("Auth provider unavailable");
  },
  logout: async () => undefined,
  refreshUser: async () => null,
};

const AuthContext = createContext<AuthContextValue>(defaultContext);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const clearNotice = () => setNotice(null);

  const refreshUser = async (): Promise<AuthUser | null> => {
    try {
      const response = await fetchCurrentUser();
      setUser(response.user);
      setNotice(null);
      return response.user;
    } catch (error) {
      if (isApiError(error) && error.kind === "auth") {
        setUser(null);
        if (error.message === SESSION_EXPIRED_MESSAGE) {
          setNotice(SESSION_EXPIRED_MESSAGE);
          try {
            await logoutUser();
          } catch {
            // Ignore cleanup failures and keep the session cleared in memory.
          }
        } else if (error.message !== LOGIN_REQUIRED_MESSAGE) {
          setNotice(error.message);
        }
        return null;
      }

      setUser(null);
      setNotice(GENERIC_RETRY_MESSAGE);
      return null;
    }
  };

  useEffect(() => {
    let active = true;

    void (async () => {
      await refreshUser();
      if (!active) {
        return;
      }
      setIsLoading(false);
    })();

    return () => {
      active = false;
    };
  }, []);

  const login = async (payload: AuthPayload): Promise<AuthUser> => {
    const response = await loginUser(payload);
    setUser(response.user);
    setNotice(null);
    return response.user;
  };

  const register = async (payload: AuthPayload): Promise<AuthUser> => {
    const response = await registerUser(payload);
    setUser(response.user);
    setNotice(null);
    return response.user;
  };

  const logout = async (): Promise<void> => {
    try {
      await logoutUser();
    } finally {
      setUser(null);
      setNotice(null);
    }
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      notice,
      clearNotice,
      login,
      register,
      logout,
      refreshUser,
    }),
    [isLoading, notice, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);
