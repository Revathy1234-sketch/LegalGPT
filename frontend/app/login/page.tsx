"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import Link from "next/link";
import { Bot, Lock, Mail, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { authApi } from "@/src/lib/api/auth";
import { useState } from "react";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

export default function Login() {
  const router = useRouter();
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    }
  });

  const [serverError, setServerError] = useState<string | null>(null);

  const loginMutation = useMutation({
    mutationFn: async (data: z.infer<typeof loginSchema>) => {
      const params = new URLSearchParams();
      params.append('username', data.email);
      params.append('password', data.password);
      return authApi.login(params);
    },
    onSuccess: (response) => {
      localStorage.setItem('access_token', response.access_token);
      router.push("/");
    },
    onError: (error: { response?: { status?: number } } | Error | unknown) => {
      const err = error as { response?: { status?: number } };
      if (err.response?.status === 401) {
        setServerError("Invalid email or password");
      } else {
        setServerError("An error occurred during login. Please try again.");
      }
    }
  });

  const onSubmit = (data: z.infer<typeof loginSchema>) => {
    setServerError(null);
    loginMutation.mutate(data);
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-slate-50 selection:bg-blue-100 selection:text-blue-900">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="p-3 bg-blue-600 rounded-xl shadow-sm">
            <Bot className="h-8 w-8 text-white" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-slate-900">
          Sign in to LegalGPT
        </h2>
        <p className="mt-2 text-center text-sm text-slate-700/80">
          Or{" "}
          <Link href="/register" className="font-medium text-blue-600 hover:text-blue-500 transition-colors">
            create a new account
          </Link>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-sm sm:rounded-xl border border-slate-200 sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            <div>
              <label className="block text-sm font-medium text-slate-700">Email address</label>
              <div className="mt-2 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-700/40" />
                </div>
                <input
                  type="email"
                  {...register("email")}
                  className="block w-full pl-10 py-2 sm:text-sm border border-slate-200/80 rounded-md focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition-colors bg-slate-50 focus:bg-white"
                  placeholder="you@example.com"
                />
              </div>
              {errors.email && <p className="mt-1 text-sm text-rose-600">{errors.email.message?.toString()}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700">Password</label>
              <div className="mt-2 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-700/40" />
                </div>
                <input
                  type="password"
                  {...register("password")}
                  className="block w-full pl-10 py-2 sm:text-sm border border-slate-200/80 rounded-md focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition-colors bg-slate-50 focus:bg-white"
                  placeholder="••••••••"
                />
              </div>
              {errors.password && <p className="mt-1 text-sm text-rose-600">{errors.password.message?.toString()}</p>}
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-blue-600 focus:ring-blue-600 border-slate-200/80 rounded outline-none"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-900">
                  Remember me
                </label>
              </div>
            </div>

            {serverError && (
              <div className="p-3 text-sm text-rose-600 bg-rose-50 rounded-md border border-rose-100">
                {serverError}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loginMutation.isPending}
                className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-600/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loginMutation.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  "Sign in"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
