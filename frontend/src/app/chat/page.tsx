"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ChatWindow from "../../components/ChatWindow";

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.push("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;
  return <ChatWindow />;
}
