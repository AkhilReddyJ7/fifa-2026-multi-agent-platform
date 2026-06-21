"use client";
import { useRouter } from "next/navigation";
import LoginForm from "../../components/LoginForm";

export default function LoginPage() {
  const router = useRouter();
  return (
    <main className="flex items-center justify-center min-h-screen px-4">
      <LoginForm onSuccess={() => router.replace("/chat")} />
    </main>
  );
}
