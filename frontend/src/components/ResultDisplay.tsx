import { useState } from "react"
import { CheckCircle, XCircle, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "./ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible"
import type { MatchResponse } from "../types/api"

interface ResultDisplayProps {
  result: MatchResponse
}

export function ResultDisplay({ result }: ResultDisplayProps) {
  const [isOpen, setIsOpen] = useState(false)

  const getStatusIcon = () => {
    if (result.decision === "match") {
      return <CheckCircle className="h-8 w-8 text-green-500" />
    } else {
      return <XCircle className="h-8 w-8 text-red-500" />
    }
  }

  const getStatusColor = () => {
    return result.decision === "match" ? "text-green-600" : "text-red-600"
  }

  const getStatusText = () => {
    return result.decision === "match" ? "Match Found" : "No Match"
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <CardTitle className={getStatusColor()}>
              {getStatusText()}
            </CardTitle>
            <CardDescription>
              Stage {result.stage} analysis completed
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Name Similarity Score</p>
            <p className="text-2xl font-bold">{result.score}/100</p>
            <p className="text-xs text-muted-foreground mt-1">
              How similar the names are (Stage 1)
            </p>
          </div>
          {result.confidence && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">AI Confidence</p>
              <p className="text-2xl font-bold">
                {(result.confidence * 100).toFixed(0)}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                How certain the LLM is about the final decision (Stage 2)
              </p>
            </div>
          )}
        </div>

        <div>
          <p className="text-sm font-medium text-muted-foreground mb-2">
            {result.stage === 2 ? "LLM Validation Analysis Explanation" : "Explanation"}
          </p>
          <p className="text-sm">{result.explanation}</p>
          {result.stage === 2 && (
            <p className="text-xs text-muted-foreground mt-2">
              ⚡ This result was reviewed by LLM analysis due to borderline name similarity or conflicts detected in Stage 1.
            </p>
          )}
        </div>

        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger asChild>
            <Button variant="outline" className="w-full">
              {isOpen ? (
                <>
                  <ChevronUp className="h-4 w-4 mr-2" />
                  Hide Details
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4 mr-2" />
                  Show Details
                </>
              )}
            </Button>
          </CollapsibleTrigger>
          
          <CollapsibleContent className="space-y-4 mt-4">
            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Stage 1 Results</h4>
                <div className="bg-muted p-3 rounded-md text-sm space-y-2">
                  <p><strong>Decision:</strong> {result.details.stage1.decision}</p>
                  <p><strong>Score:</strong> {result.details.stage1.score}</p>
                  <p><strong>Best Match:</strong> {result.details.stage1.best_person}</p>
                  <p><strong>Variant Used:</strong> {result.details.stage1.candidate_variant}</p>
                  {result.details.stage1.penalty > 0 && (
                    <p><strong>Penalty:</strong> {result.details.stage1.penalty}</p>
                  )}
                </div>
              </div>

              {result.details.stage2 && (
                <div>
                  <h4 className="font-medium mb-2">Stage 2 Results</h4>
                  <div className="bg-muted p-3 rounded-md text-sm space-y-2">
                    <p><strong>Decision:</strong> {result.details.stage2.decision}</p>
                    <p><strong>Confidence:</strong> {(result.details.stage2.confidence * 100).toFixed(1)}%</p>
                    <p><strong>Evidence:</strong> {result.details.stage2.evidence_sentence}</p>
                  </div>
                </div>
              )}

              <div>
                <h4 className="font-medium mb-2">Raw JSON</h4>
                <pre className="bg-muted p-3 rounded-md text-xs overflow-auto">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  )
} 