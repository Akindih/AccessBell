import { useEffect, useState } from "react";

const PI_URL = "http://<YOUR_PI_IP>:8000";

export interface VisitHistory {
  visit_id: number;
  recognised: boolean;
  confidence: number;
  visited_at: string;
}

export interface Visitor {
  person_id: number;
  full_name: string;
  relationship: string;
  last_seen: string;
  history: VisitHistory[];
}

export function useVisitor(pollInterval = 3000) {
  const [visitor, setVisitor] = useState<Visitor | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${PI_URL}/visitor`);
        const data = await res.json();
        setVisitor(data.visitor);
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
