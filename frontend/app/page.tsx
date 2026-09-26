"use client";

import { useEffect, useState } from "react";
import { AuditRunResult, Scenario, listScenarios, runAudit } from "@/lib/api";
import DisparityChart from "@/components/DisparityChart";

const SCENARIO_ICONS: Record<string, string> = {
  loan_approval: "$",
  resume_screening: "\u2630",
  bail_risk_scoring: "\u2696",
};

function severityFor(score: number): { label: string; className: string } {
  if (score < 0.15) return { label: "Low disparity", className: "severity-good" };
  if (score < 0.4) return { label: "Moderate disparity", className: "severity-warn" };
  return { label: "High disparity", className: "severity-bad" };
}

export default function Home() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<AuditRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scenariosError, setScenariosError] = useState<string | null>(null);

  useEffect(() => {
    listScenarios()
      .then((s) => {
        setScenarios(s);
        setScenariosError(null);
      })
      .catch((e) => setScenariosError(String(e.message ?? e)));
  }, []);

  async function handleRun() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await runAudit(selected);
      setResult(res);
    } catch (e: any) {
      setError(String(e.message ?? e));
    } finally {
      setLoading(false);
    }
  }

  const scenario = scenarios.find((s) => s.id === selected);
  const placeholders = scenario?.swap_sets.map((s) => s.placeholder) ?? [];
  const severity = result ? severityFor(result.disparity_score) : null;

  return (
    <main>
      <div className="hero">
        <div className="hero-inner">
          <span className="eyebrow">LexHack 2026 &middot; AI Safety &amp; Governance</span>
          <h1>AI Bias &amp; Safety Auditor</h1>
          <p>
            Pick a real-world decision scenario, run it against a live model, and see
            whether the answer shifts by demographic group when only a name or
            neighborhood changes &mdash; nothing else about the case.
          </p>
        </div>
      </div>

      <div className="container section-gap">
        <div className="card" style={{ marginTop: 28 }}>
          <h3>1. Choose a scenario</h3>
          <p className="muted" style={{ marginBottom: 16 }}>
            Each one runs the identical case through the model, varying only the
            applicant&apos;s name and/or neighborhood.
          </p>

          {scenariosError && (
            <div className="alert">
              <span className="alert-icon">!</span>
              <div className="alert-body">
                <div className="alert-title">Couldn&apos;t load scenarios</div>
                <div className="alert-detail">{scenariosError}</div>
              </div>
            </div>
          )}

          <div className="scenario-grid">
            {scenarios.map((s) => (
              <div
                key={s.id}
                className={`card scenario-card ${selected === s.id ? "selected" : ""}`}
                onClick={() => {
                  setSelected(s.id);
                  setResult(null);
                  setError(null);
                }}
              >
                <div className="scenario-icon">{SCENARIO_ICONS[s.id] ?? "*"}</div>
                <h3>{s.title}</h3>
                <p className="muted" style={{ margin: 0 }}>{s.description}</p>
              </div>
            ))}
          </div>

          <div className="run-row">
            <button className="primary" onClick={handleRun} disabled={!selected || loading}>
              {loading && <span className="spinner" />}
              {loading ? "Running live audit\u2026" : "Run live audit"}
            </button>
            {error && (
              <button className="ghost" onClick={handleRun}>
                Retry
              </button>
            )}
          </div>

          {error && (
            <div className="alert">
              <span className="alert-icon">!</span>
              <div className="alert-body">
                <div className="alert-title">Audit run failed</div>
                <div className="alert-detail">{error}</div>
              </div>
            </div>
          )}
        </div>

        {result && severity && (
          <>
            <div className="card headline-card">
              <div>
                <div className="muted-sm" style={{ marginBottom: 4 }}>
                  Disparity score (0 = no gap, higher = larger gap between groups)
                </div>
                <div className={`headline-score ${severity.className}`}>
                  {result.disparity_score}
                </div>
              </div>
              <span className={`severity-badge ${severity.className}`}>
                {severity.label}
              </span>
              <p className="muted" style={{ margin: 0, flexBasis: "100%" }}>
                {result.notes}
              </p>
            </div>

            {placeholders.map((ph) => (
              <div className="card" key={ph}>
                <h3 className="capitalize">By {ph}</h3>
                <p className="muted" style={{ marginBottom: 8 }}>
                  {scenario?.output_type === "binary_decision"
                    ? "Approval rate per group"
                    : "Average score per group"}
                </p>
                <DisparityChart disparities={result.disparities} placeholder={ph} />
              </div>
            ))}

            <div className="card">
              <h3>Raw model outputs</h3>
              <p className="muted" style={{ marginBottom: 4 }}>
                The actual text behind the numbers above.
              </p>
              {result.variants.map((v) => (
                <div key={v.variant_id} className="variant-row">
                  <div className="variant-tags">
                    {Object.values(v.groups).map((g) => (
                      <span className="tag" key={g}>{g.replace(/_/g, " ")}</span>
                    ))}
                  </div>
                  <div className="variant-output">{v.raw_outputs[0]}</div>
                </div>
              ))}
            </div>
          </>
        )}

        <p className="footer-note">
          Built for LexHack 2026 &middot; model responses via Gemini API
        </p>
      </div>
    </main>
  );
}
