"use client";
import { useRouter } from "next/navigation";
import RegisterForm from "../../components/RegisterForm";

export default function RegisterPage() {
  const router = useRouter();
  return (
    <main className="flex items-center justify-center min-h-screen px-4">
      <RegisterForm onSuccess={() => router.replace("/login")} />
    </main>
  );
}
