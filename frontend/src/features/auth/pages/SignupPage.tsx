import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSignup } from "@/shared/queries/auth";

// helper to read CSRF token from cookies
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  const value = match?.[2];
  return value ? decodeURIComponent(value) : null;
}

export default function SignupPage() {
  const navigate = useNavigate();
  const signupMutation = useSignup();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check if passwords match before submitting
    if (password !== passwordConfirm) {
      return;
    }

    try {
      await signupMutation.mutateAsync({ username, email, password });
      navigate("/deepdive");
    } catch (error) {
      console.error("Signup failed:", error);
    }
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-50">
      <form
        onSubmit={handleSignup}
        className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm"
      >
        <h2 className="text-xl font-semibold mb-4 text-center">Sign Up</h2>

        {(signupMutation.error || (password !== passwordConfirm && passwordConfirm !== "")) && (
          <div className="bg-red-100 text-red-700 text-sm p-2 rounded mb-4">
            {password !== passwordConfirm && passwordConfirm !== "" ? "Passwords do not match." : signupMutation.error?.message}
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
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-4 py-2 mb-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-2 mb-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <input
          type="password"
          placeholder="Confirm Password"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          className="w-full px-4 py-2 mb-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <button
          type="submit"
          disabled={signupMutation.isPending}
          className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition disabled:opacity-50"
        >
          {signupMutation.isPending ? "Signing up..." : "Sign Up"}
        </button>
      </form>
    </div>
  );
}
