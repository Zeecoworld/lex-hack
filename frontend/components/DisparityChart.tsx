"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { GroupDisparity } from "@/lib/api";

interface Props {
  disparities: GroupDisparity[];
  placeholder: string; // which swap dimension to chart, e.g. "name"
}

const PALETTE = ["#4f46e5", "#7c6cf6", "#06b6d4", "#f59e0b", "#ec4899", "#10b981"];

export default function DisparityChart({ disparities, placeholder }: Props) {
  const data = disparities
    .filter((d) => d.placeholder === placeholder)
    .map((d) => ({
      group: d.group.replace(/_/g, " "),
      score:
        d.approval_rate !== null && d.approval_rate !== undefined
          ? Math.round(d.approval_rate * 100)
          : Math.round(d.mean_score * 100) / 100,
      n: d.n,
    }));

  if (data.length === 0) return null;

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef0f5" vertical={false} />
          <XAxis
            dataKey="group"
            angle={-20}
            textAnchor="end"
            interval={0}
            height={60}
            tick={{ fontSize: 12, fill: "#6b6b78" }}
            axisLine={{ stroke: "#e6e6ee" }}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 12, fill: "#6b6b78" }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              borderRadius: 10,
              border: "1px solid #e6e6ee",
              fontSize: 13,
            }}
            formatter={(value: number, _name, props) => [
              `${value} (n=${props.payload.n})`,
              "score",
            ]}
          />
          <Bar dataKey="score" radius={[6, 6, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
