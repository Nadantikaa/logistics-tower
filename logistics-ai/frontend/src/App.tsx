import { LoginScreen } from "./components/LoginScreen";
import { useAuth } from "./context/AuthContext";
import { Dashboard } from "./pages/Dashboard";

export default function App() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <main className="login-shell">Loading...</main>;
  }

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return <Dashboard />;
}
