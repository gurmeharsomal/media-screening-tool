import { useState } from "react"
import { MatchForm } from "./components/MatchForm"
import { ResultDisplay } from "./components/ResultDisplay"
import { matchCandidate } from "./lib/api"
import type { Candidate, MatchResponse } from "./types/api"

function App() {
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (candidate: Candidate, article: string) => {
    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await matchCandidate({ candidate, article })
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="container mx-auto space-y-8">
        <header className="text-center">
          <h1 className="text-4xl font-bold tracking-tight">Media Screening Tool</h1>
          <p className="text-muted-foreground mt-2">
            Two-stage pipeline for candidate-article matching
          </p>
        </header>

        <MatchForm onSubmit={handleSubmit} isLoading={isLoading} />

        {error && (
          <div className="w-full max-w-2xl mx-auto">
            <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md">
              <p className="font-medium">Error</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {result && <ResultDisplay result={result} />}
      </div>
    </div>
  )
}

export default App
