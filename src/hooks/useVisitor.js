import { useEffect, useState } from "react";

const PI_URL = "http://<YOUR_PI_IP>:8000";

export function useVisitor(pollInterval = 3000) {
  const [visitor, setVisitor] = useState(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${PI_URL}/visitor`);
        const data = await res.json();
        setVisitor(data?.visitor ?? null);
      } catch (e) {
        console.error("Failed to reach Pi API", e);
      }
    };

    poll();
    const interval = setInterval(poll, pollInterval);
    return () => clearInterval(interval);
  }, [pollInterval]);

  return visitor;
}
