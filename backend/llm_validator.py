import hashlib
import json
import os
from functools import lru_cache
from typing import Dict, Any
import openai
from dotenv import load_dotenv
from models import Candidate, Stage2Result
from rule_engine import extract_person_entities, check_attribute_conflicts

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = openai.OpenAI(api_key=api_key)

SYSTEM_PROMPT = """You are a senior adverse media analyst conducting second-stage validation.
You review borderline cases from a first-stage name matcher. Your job is to CONFIRM or REJECT a candidate/article match.

Your role is to catch nuanced matches that automated systems miss and eliminate false positives and false negatives through careful contextual analysis.

HARD CONSTRAINTS (must-follow rules):
1) You may only return "match" if the article excerpt contains a VERBATIM mention of the candidate's name or one of the provided all generated name variants. If none are present, return "no_match".
2) Do not equate phonetically similar or semantically related names unless they appear exactly as one of allowed_variants.
3) Base your analysis ONLY on information present in the excerpt and the stage-1 facts; do not invent external facts.
4) Prefer precision and caution: if unsure, return "no_match" with reasons.


CRITICAL RULES:
- Base analysis ONLY on information present in the article. Do not infer facts not explicitly stated or implied.
- Do NOT create connections between unrelated people mentioned in the article.
- If the name variant used in Stage 1 doesn't make logical sense (e.g., "Megan" vs "Michael"), this is likely a false positive.
- A single name should not match a full name unless it's a clear nickname or initial.
- Focus on the specific person mentioned in the article, not other people in the same context.
- OCCUPATION CONFLICTS ARE AUTOMATIC DISQUALIFIERS: If the article clearly states an INCOMPATIBLE profession (e.g., "Dr. X" vs attorney, "Judge Y" vs engineer), this is a NO_MATCH regardless of name similarity.
- OCCUPATION COMPATIBILITY: Related professions are compatible (e.g., "doctor" vs "cardiologist", "teacher" vs "professor", "lawyer" vs "attorney").
- Do NOT make excuses for occupation conflicts (e.g., "people can have multiple roles", "attorneys can be involved in healthcare"). If the article says "Dr. X" and candidate is an attorney, it's a NO_MATCH.
- If there's any doubt about the connection, default to "no_match".

DECISION FRAMEWORK:
- "match": The excerpt explicitly mentions a name from allowed_variants AND context is consistent (no occupation conflicts, age conflicts, etc.)
- "no_match": The excerpt lacks an allowed variant OR contains contradictions (occupation conflicts, age conflicts, etc.)

IMPORTANT: Your "reasons" explanation must match your "decision". If you say "match" in decision, your reasons should explain why it's a match. If you say "no_match" in decision, your reasons should explain why it's not a match.

ANALYSIS PRIORITIES:
1. Contextual biographical alignment (age references, career timeline, locations)
2. Implicit references (pronouns, titles, "the executive", "the former CEO")
3. Temporal consistency (does timeline make sense for this person?)
4. Disambiguation signals (middle names, specific affiliations, unique details, occupation)
5. Contradictory evidence that suggests different person

Respond with strict JSON format only, including a "reasons" field with plain English explanation."""

USER_PROMPT_TEMPLATE = """Candidate Profile:
- Name: {name}
- Date of Birth: {dob}
- Occupation: {occupation}

Stage 1 Analysis Results:
- Best Match Found: {best_person}
- Candidate Name Variant Used: {candidate_variant}
- All Generated Name Variants: {all_variants}
- Fuzzy Match Score: {score}/100
- Penalty Applied: {penalty} points
- Stage 1 Decision: {stage1_decision}
- Stage 1 Reasoning: {stage1_reasons}
- Names Found in Article: {extracted_names}

Additional Conflict Analysis:
- DOB Conflicts: {dob_conflicts}
- Occupation Conflicts: {occupation_conflicts}

Article Excerpt:
{excerpt}

NAME VALIDATION CHECKLIST:
1. Is the candidate name variant a reasonable expansion of the original name?
   - Nicknames: "Bob" for "Robert" (correct), "Megan" for "Michael" (wrong)
   - Initials: "J. Smith" for "John Smith" (correct)
   - Middle names: "Michael Davis" for "John Michael Davis" (correct)
   - Substrings: "Mora" for "Alex Morales" (likely false positive)

2. Is this a single name vs full name match?
   - Single names should rarely match full names unless they're clear nicknames
   - Be extra cautious with substring matches

3. OCCUPATION CONFLICT CHECK (CRITICAL):
   - Does the article mention a different profession than the candidate's occupation?
   - Check if they are compatible (e.g., "doctor" vs "cardiologist" = compatible)
   - Check if they are incompatible (e.g., "doctor" vs "attorney" = incompatible)
   - If INCOMPATIBLE, this is an automatic NO_MATCH regardless of name similarity
   - Examples of incompatibility: "Dr. X" vs attorney, "Judge Y" vs engineer, "Professor Z" vs police officer
   - Examples of compatibility: "Dr. X, cardiologist" vs "X, doctor", "Professor Y" vs "Y, teacher"
   - Do NOT make excuses for occupation conflicts

Based on the Stage 1 analysis above, determine if this article is about the candidate. Consider:
1. The fuzzy match score and any penalties applied
2. Whether the name variant makes logical sense (e.g., "Bob" for "Robert" is reasonable, "Megan" for "Michael" is not)
3. Whether the best match found in the article corresponds to any of the allowed name variants
4. Any conflicts detected in Stage 1
5. Additional DOB and occupation conflicts found in Stage 2
6. Additional context from the article excerpt
7. All names found in the article and their relevance

Pay special attention to:
- Age discrepancies (e.g., candidate born 1980 but article mentions 25-year-old)
- OCCUPATION CONFLICTS: These are AUTOMATIC DISQUALIFIERS for INCOMPATIBLE professions. However, COMPATIBLE professions are acceptable like:
  * "Doctor" is compatible with: cardiologist, surgeon, physician, specialist, etc.
  * "Teacher" is compatible with: professor, instructor, educator, etc.
  * "Lawyer" is compatible with: attorney, counsel, prosecutor, etc.
  * "Police" is compatible with: officer, detective, investigator, etc.
- Timeline inconsistencies
- Location or context mismatches
- Name variant logic: If the candidate name variant doesn't make sense (e.g., "Megan" vs "Michael Tanner"), this is likely a false positive
- Substring name issues: Be very cautious when a single name matches part of a full name (e.g., "Mora" vs "Alex Morales")
- Verify that the best match found corresponds to one of the allowed name variants
- Check if the name variant is a reasonable expansion of the candidate's name

OCCUPATION CONFLICT EXAMPLES:
- Article: "Dr. Alex Morales, cardiology specialist" vs Candidate: "Alex Morales, attorney" is NO_MATCH
- Article: "Judge Smith" vs Candidate: "John Smith, engineer" is NO_MATCH  
- Article: "Professor Johnson" vs Candidate: "Robert Johnson, police officer" is NO_MATCH

OCCUPATION COMPATIBILITY EXAMPLES (THESE ARE MATCHES):
- Article: "Dr. Alex Morales, cardiology specialist" vs Candidate: "Alex Morales, doctor" is MATCH
- Article: "Dr. Smith, surgeon" vs Candidate: "John Smith, physician" is MATCH
- Article: "Professor Johnson, mathematics" vs Candidate: "Robert Johnson, teacher" is MATCH
- Article: "Attorney Davis" vs Candidate: "Michael Davis, lawyer" is MATCH
- Article: "Detective Wilson" vs Candidate: "Sarah Wilson, police officer" is MATCH

OCCUPATION HIERARCHY RULES:
- "Doctor" includes: physician, surgeon, cardiologist, specialist, pediatrician, etc.
- "Teacher" includes: professor, instructor, educator, lecturer, etc.
- "Lawyer" includes: attorney, counsel, prosecutor, defense attorney, etc.
- "Police" includes: officer, detective, investigator, sergeant, etc.
- "Engineer" includes: software engineer, civil engineer, mechanical engineer, etc.

Do NOT rationalize occupation conflicts with excuses like "people can have multiple roles" or "professionals can be involved in different fields".

Respond with JSON:
{{"decision": "match|no_match", "confidence": 0.0-1.0, "evidence_sentence": "key sentence from excerpt", "reasons": "plain English explanation of your decision"}}"""


@lru_cache(maxsize=1000)
def cached_llm_validation(profile_json: str, excerpt: str, stage1_results: str) -> Stage2Result:
    """Cached LLM validation to avoid repeated API calls."""
    profile = json.loads(profile_json)
    
    dob = profile.get('dob', 'Not provided')
    occupation = profile.get('occupation', 'Not provided')
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        name=profile['name'],
        dob=dob,
        occupation=occupation,
        excerpt=excerpt,
        **json.loads(stage1_results)
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return Stage2Result(
            decision=result["decision"],
            confidence=result["confidence"],
            evidence_sentence=result["evidence_sentence"],
            reasons=result.get("reasons", "No explanation provided by LLM")
        )
        
    except Exception as e:
        return Stage2Result(
            decision="no_match",
            confidence=0.0,
            evidence_sentence=f"Error during LLM validation: {str(e)}",
            reasons=f"LLM validation failed due to error: {str(e)}"
        )


def stage2_validate(candidate: Candidate, article_excerpt: str, stage1_result, full_article: str = None) -> Stage2Result:
    """Stage 2: LLM-based validation for borderline cases."""
    profile = {
        "name": candidate.name,
        "dob": candidate.dob,
        "occupation": candidate.occupation
    }
    
    profile_json = json.dumps(profile, sort_keys=True)
    
    text_for_name_extraction = full_article if full_article else article_excerpt
    extracted_names = extract_person_entities(text_for_name_extraction)
    extracted_names_str = ", ".join(extracted_names) if extracted_names else "None found"
    
    text_for_conflict_check = full_article if full_article else article_excerpt
    _, conflict_explanation = check_attribute_conflicts(candidate, text_for_conflict_check, stage1_result.best_person)
    
    dob_conflicts = "None detected"
    occupation_conflicts = "None detected"
    
    if "DOB conflict" in conflict_explanation:
        dob_conflicts = conflict_explanation.split("Occupation")[0].strip()
    if "Occupation" in conflict_explanation:
        occupation_conflicts = conflict_explanation.split("Occupation")[1].strip()
    
    stage1_results = {
        "best_person": stage1_result.best_person,
        "candidate_variant": stage1_result.candidate_variant,
        "all_variants": stage1_result.all_variants,
        "score": stage1_result.score,
        "penalty": stage1_result.penalty,
        "stage1_decision": stage1_result.decision,
        "stage1_reasons": stage1_result.reasons,
        "extracted_names": extracted_names_str,
        "dob_conflicts": dob_conflicts,
        "occupation_conflicts": occupation_conflicts
    }
    stage1_results_json = json.dumps(stage1_results, sort_keys=True)
    
    result = cached_llm_validation(profile_json, article_excerpt, stage1_results_json)
    
    if result.confidence < 0.8:
        result.decision = "no_match"
    
    return result 