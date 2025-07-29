import React, { useState } from "react";

interface MatchFormProps {
  onSubmit: (candidate: { name: string; dob: string; occupation: string }, article: string) => void;
  isLoading: boolean;
}

export function MatchForm({ onSubmit, isLoading }: MatchFormProps) {
  const [candidate, setCandidate] = useState({ name: "", dob: "", occupation: "" });
  const [article, setArticle] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (candidate.name.trim() && article.trim()) {
      onSubmit(candidate, article);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 600, margin: "2rem auto", padding: 24, border: "1px solid #eee", borderRadius: 8, background: "#fff" }}>
      <h2 style={{ marginBottom: 16 }}>Media Screening Tool</h2>
      <div style={{ marginBottom: 16 }}>
        <label>
          Candidate Name *
          <input
            type="text"
            value={candidate.name}
            onChange={e => setCandidate({ ...candidate, name: e.target.value })}
            placeholder="e.g., William Gates"
            required
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 16 }}>
        <label>
          Date of Birth
          <input
            type="date"
            value={candidate.dob}
            onChange={e => setCandidate({ ...candidate, dob: e.target.value })}
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 16 }}>
        <label>
          Occupation
          <input
            type="text"
            value={candidate.occupation}
            onChange={e => setCandidate({ ...candidate, occupation: e.target.value })}
            placeholder="e.g., Software Engineer"
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 16 }}>
        <label>
          News Article *
          <textarea
            value={article}
            onChange={e => setArticle(e.target.value)}
            placeholder="Paste the full article text here..."
            required
            style={{ display: "block", width: "100%", minHeight: 120, marginTop: 4, padding: 8, borderRadius: 4, border: "1px solid #ccc" }}
          />
        </label>
      </div>
      <button type="submit" disabled={isLoading} style={{ width: "100%", padding: 12, fontWeight: "bold", borderRadius: 4, background: "#222", color: "#fff", border: "none", cursor: isLoading ? "not-allowed" : "pointer" }}>
        {isLoading ? "Analyzing..." : "Check for Matches"}
      </button>
    </form>
  );
} 