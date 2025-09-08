import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin, useCsrfToken } from "@/shared/queries/auth";
import { config } from "@/config";

// helper to read CSRF token from cookies
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  const value = match?.[2];
  return value ? decodeURIComponent(value) : null;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLogin();
  const { data: csrfData } = useCsrfToken();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await loginMutation.mutateAsync({ username, password });
      navigate("/deepdive");
    } catch (error) {
      // Error is handled by the mutation
      console.error("Login failed:", error);
    }
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-50">
      <form
        onSubmit={handleLogin}
        className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm"
      >
        <h2 className="text-xl font-semibold mb-4 text-center">Log In</h2>

        {loginMutation.error && (
          <div className="bg-red-100 text-red-700 text-sm p-2 rounded mb-4">
            {loginMutation.error.message}
          </div>
        )}

        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full px-4 py-2 mb-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-2 mb-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <button
          type="submit"
          disabled={loginMutation.isPending}
          className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition disabled:opacity-50"
        >
          {loginMutation.isPending ? "Logging in..." : "Log In"}
        </button>
      </form>
    </div>
  );
}
