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

import { useVisitor } from "@/hooks/useVisitor";

export default function VisitorCard() {
  const visitor = useVisitor(3000);

  if (!visitor) {
    return (
      <div className="p-6 rounded-2xl bg-gray-100 text-gray-500 text-center">
        No visitor detected yet.
      </div>
    );
  }

  return (
    <div className="p-6 rounded-2xl bg-white shadow-md space-y-4">
      <div>
        <h2 className="text-2xl font-bold">{visitor.full_name}</h2>
        <p className="text-gray-500">{visitor.relationship}</p>
        <p className="text-sm text-gray-400">
          Last seen: {new Date(visitor.last_seen).toLocaleString()}
        </p>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Visit History</h3>
        <ul className="space-y-1 text-sm">
          {visitor.history.map((v) => (
            <li key={v.visit_id} className="flex justify-between border-b py-1">
              <span>{new Date(v.visited_at).toLocaleString()}</span>
              <span className={v.recognised ? "text-green-600" : "text-red-500"}>
                {v.recognised ? `✓ ${(v.confidence * 100).toFixed(1)}%` : "Unrecognised"}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
