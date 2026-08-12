import { useState } from "react";
import { authApi, saveSession } from "../services/authSession";

type AuthPageProps = { onAuthenticated: () => void };

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [message, setMessage] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    const result = mode === "login"
      ? await authApi.login({ email, password })
      : await authApi.register({ display_name: displayName, email, password });
    if (result.error) {
      setMessage(result.error.message);
      return;
    }
    saveSession(result.data);
    onAuthenticated();
  }

  return <main className="auth-page"><section className="auth-panel">
    <div className="auth-brand">945</div>
    <h1>{mode === "login" ? "登录 945" : "创建 945 账号"}</h1>
    <form onSubmit={submit}>
      {mode === "register" && <label>昵称<input required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>}
      <label>邮箱<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>密码<input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {message && <p className="auth-error">{message}</p>}
      <button type="submit">{mode === "login" ? "登录" : "注册并开始"}</button>
    </form>
    <button className="auth-switch" onClick={() => setMode(mode === "login" ? "register" : "login")} type="button">
      {mode === "login" ? "没有账号？创建账号" : "已有账号？登录"}
    </button>
  </section></main>;
}
