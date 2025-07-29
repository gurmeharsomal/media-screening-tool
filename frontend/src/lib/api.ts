import { MatchResponseSchema } from "../types/api"
import type { MatchRequest, MatchResponse } from "../types/api"

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export async function matchCandidate(request: MatchRequest): Promise<MatchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/match`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  
  // Validate response with Zod
  const validatedData = MatchResponseSchema.parse(data)
  
  return validatedData
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`)
    return response.ok
  } catch {
    return false
  }
} 