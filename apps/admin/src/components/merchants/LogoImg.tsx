"use client";

import { Building2 } from "lucide-react";
import { useState } from "react";

/** L60: merchant logo with an icon fallback when the image URL is missing or dead. */
export function LogoImg({
  src,
  iconClassName = "h-6 w-6",
}: {
  src?: string | null;
  iconClassName?: string;
}) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) return <Building2 className={iconClassName} aria-hidden />;
  // eslint-disable-next-line @next/next/no-img-element
  return (
    <img src={src} alt="" className="h-full w-full object-cover" onError={() => setBroken(true)} />
  );
}
