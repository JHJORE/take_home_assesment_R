"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function UploadGate() {
  const router = useRouter();
  useEffect(() => {
    if (sessionStorage.getItem("readily:uploaded") !== "1") {
      router.replace("/upload");
    }
  }, [router]);
  return null;
}
