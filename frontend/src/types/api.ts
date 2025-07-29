import { z } from "zod"

// API Request/Response schemas
export const CandidateSchema = z.object({
  name: z.string().min(1, "Name is required"),
  dob: z.string().optional(),
  occupation: z.string().optional(),
})

export const MatchRequestSchema = z.object({
  candidate: CandidateSchema,
  article: z.string().min(1, "Article text is required"),
})

export const Stage1ResultSchema = z.object({
  stage: z.literal(1),
  decision: z.enum(["match", "no_match", "review"]),
  score: z.number().min(0).max(100),
  best_person: z.string(),
  candidate_variant: z.string(),
  all_variants: z.string(),
  penalty: z.number().min(0).max(100),
  reasons: z.string(),
})

export const Stage2ResultSchema = z.object({
  decision: z.enum(["match", "no_match"]),
  confidence: z.number().min(0).max(1),
  evidence_sentence: z.string(),
  reasons: z.string(),
})

export const MatchResponseSchema = z.object({
  decision: z.enum(["match", "no_match"]),
  stage: z.number().min(1).max(2),
  score: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1).nullable(),
  explanation: z.string(),
  details: z.object({
    stage1: Stage1ResultSchema,
    stage2: Stage2ResultSchema.optional(),
  }),
})

// TypeScript types
export type Candidate = z.infer<typeof CandidateSchema>
export type MatchRequest = z.infer<typeof MatchRequestSchema>
export type MatchResponse = z.infer<typeof MatchResponseSchema>
export type Stage1Result = z.infer<typeof Stage1ResultSchema>
export type Stage2Result = z.infer<typeof Stage2ResultSchema> 