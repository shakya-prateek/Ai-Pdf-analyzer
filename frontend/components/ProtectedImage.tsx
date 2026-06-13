"use client";

import { useEffect, useState } from "react";
import { fetchProtectedImage } from "@/lib/api";

export function ProtectedImage({
  path,
  alt,
  className
}: {
  path: string;
  alt: string;
  className?: string;
}) {
  const [source, setSource] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setSource("");
    setFailed(false);

    void fetchProtectedImage(path)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setSource(objectUrl);
      })
      .catch(() => {
        if (active) setFailed(true);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (failed) {
    return <span className="protected-image-state">Preview unavailable</span>;
  }
  if (!source) {
    return <span className="protected-image-state">Loading preview</span>;
  }
  return <img src={source} alt={alt} className={className} />;
}
