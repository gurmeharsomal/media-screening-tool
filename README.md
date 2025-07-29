# Media Screening Tool

Media Screening Tool is an adverse-media disambiguation system for regulated financial workflows. It decides whether a news article refers to a specific individual, with the twin goals of maximizing automatic discards of unrelated articles and avoiding false negatives (i.e., never labeling a true hit as no_match). The system combines a fast, deterministic filter with an LLM validator and returns auditable evidence for every decision.

## Problem & Design Objectives

Financial institutions must screen large volumes of media with near-zero tolerance for missed true hits. Our design therefore optimizes for:

1. **Operational efficiency**: automatically label unrelated articles as no_match to reduce analyst workload
2. **Risk control**: calibrate decision rules so a true positive is not labeled no_match (avoid false negatives).

We frame the task as binary classification (match / no_match) for each (candidate, article) pair and tune the pipeline to achieve high recall on true positives while maintaining strong precision for the match label.

## Approach & Architecture

### Stage 1: Deterministic Filter

Purpose: cast a wide net to protect recall, and quickly produce no_match only when there is deterministic evidence the article is not about the candidate.

- Name evidence extraction: spaCy PERSON entities + regex fallbacks; Unicode/diacritic normalization.
- Broad name handling: RapidFuzz token_set_ratio over generated variants (first+last, surname-first, initials+last, middle-as-given) and curated nicknames from the `backend/data/names.csv` dataset (e.g., Bill ↔ William, Bob ↔ Robert).
- Context checks: Lightweight detection of optional DOB/age phrases and occupation terms to surface clear contradictions.

Decision use in Stage 1:

- Output match when a strict name variant (full name, first+last, initials+last, or surname-first) appears with a strong similarity score and no conflicts are found.
- Output no_match only on rule-based contradictions (e.g., explicit DOB/age incompatible with the candidate, or complete absence of any strict variant/surname in the article).
- For borderline cases (e.g., similarity score in the 60–79 band or soft conflicts), Stage 1 defers the decision to Stage 2.

### Stage 2: LLM Validator

Purpose: resolve borderline cases using a constrained, context-aware check.

- Model & inputs: OpenAI GPT-3.5-turbo receives the candidate profile, Stage-1 findings (best span, conflicts), and a focused excerpt around the matched person.
- Validation policy: Prompts emphasize name-variant evidence and contextual coherence (DOB/age, occupation). We apply an LLM confidence threshold (≥ 0.8) for upholding a match decision.
- Caching: LRU cache (1,000 entries) avoids repeated validations for the same profile/excerpt combination.

Outcome: If Stage 2 confirms with confidence ≥ 0.8, the system returns match with an explanation sentence. Otherwise, it returns no_match with explicit reasons (e.g., variant absence or conflict).

## Explainability & Compliance

Each response returns a structured explanation: decision (match/no_match), stage used, similarity score, detected conflicts (DOB/occupation), the top name span, and an evidence sentence. We also record model/data versions (spaCy model, nickname list version, LLM model) and thresholds to support audit and reproducibility in regulated settings.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Step-by-Step Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/gurmeharsomal/media-screening-tool
   cd media-screening-tool
   ```

2. **Create environment file**

   ```bash
   # Create .env file in the root directory
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

3. **Start the application**

   ```bash
   docker compose up --build
   ```

4. **Access the application**
   - **Frontend**: http://localhost:5173
   - **Backend API**: http://localhost:8000

## Testing

### Running Tests

1. **Navigate to backend directory**

   ```bash
   cd backend
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Install spaCy models**

   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Run specific test suites**

   ```bash
   # Basic API functionality tests
   python test_api.py

   # Comprehensive edge case tests
   python test_comprehensive.py

   # Run all tests with pytest
   python -m pytest test_*.py -v
   ```

## Development

### Backend Development

1. **Set up local environment**

   ```bash
   cd backend
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. **Run development server**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Development

1. **Set up local environment**

   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**

   ```bash
   npm run dev
   ```

3. **Build for production**
   ```bash
   npm run build
   ```

## Docker Deployment

```bash
# Production build
docker compose up --build -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Part 2 Report: Automated Web Research Enrichment

This plan outlines a comprehensive system for automatically enriching adverse media screening with additional biographical data through intelligent web research. The approach addresses cases where critical disambiguating information (middle names, dates of birth, occupational details) is missing from the original article but may be found through targeted online research. The approach prioritizes efficiency, accuracy, and regulatory compliance while significantly reducing analyst manual research time.

### Problem Definition and Scope

The current screening can often produce false positives when individuals share common names or when articles lack sufficient biographical context for confident disambiguation. Analysts currently spend significant time manually researching additional biographical details to determine whether an article refers to their specific applicant.

#### Target Scenarios: Common name matches, insufficient biographical data, partial name matches, ambiguous references.

#### Success Criteria

- **Disambiguation improvement**: Significant reduction in false positives through better context
- **Research efficiency**: Significant reduction in manual research time for analysts
- **Information completeness**: Successfully enrich large amount of cases with additional biographical data
- **Accuracy maintenance**: Zero increase in false negatives (missed true matches)

### System Architecture Overview

#### Three-Layer Architecture

**Layer 1: Intelligent Trigger System**
Determines when automated research will provide value and what specific information to seek.

**Layer 2: Multi-Source Research Engine**
Executes targeted searches across authoritative data sources with source-specific extraction logic.

**Layer 3: Information Validation Framework**
Validates, cross-references, and consolidates findings from multiple sources with confidence scoring.

#### Core Assumption

The system will assume that relevant biographical information, if it exists, is available in publicly accessible authoritative sources (government filings, professional networks, reputable news archives). Private or restricted information is explicitly out of scope.

#### Core Processing Flow

```bash
  Initial Match (40-80% confidence) → Gap Analysis → Targeted Research →
  Information Validation → Enhanced Matching Decision
```

### Component 1: Intelligent Research Triggering

#### Decision Logic

The system will trigger automated research based on specific conditions rather than researching every case:

**Always Research When**:

- Initial match probability between 40-80% (ambiguous cases)
- Common names (frequency analysis of applicant database) with match probability >30%
- High name similarity (>85%) but low contextual confidence (<60%)
- Multiple potential matches identified in single article

**Never Research When**:

- Clear negative matches (<30% probability) - research unlikely to change outcome
- Clear positive matches (>80% probability) - additional context not needed for decision
- Previous research conducted within 90 days (cached results available)

**Gap Analysis**:
The system will identify specific types of missing information that could improve disambiguation:

- **Critical gaps**: Full legal names, dates of birth, unique identifiers
- **Important gaps**: Current occupation, company affiliations, educational background
- **Contextual gaps**: Historical locations, family connections, professional achievements

### Component 2: Multi-Source Research Engine

#### Source Hierarchy and Specialization

**Tier 1: Authoritative Government Sources (Reliability: 90-100%)**

- SEC EDGAR: Executive biographies from proxy statements
- Federal court records: PACER database
- Professional licensing boards
- Public property records

**Tier 2: Professional and Corporate Sources (Reliability: 70-90%)**

- LinkedIn: Career histories and current positions
- Corporate websites: Executive biography pages
- Industry associations: Member directories
- University directories (public information)

**Tier 3: Media and Archive Sources (Reliability: 50-80%)**

- News archives with biographical references
- Press release archives
- Trade publications
- Patent databases (USPTO)

#### Search Query Optimization

**Context-Driven Query Generation**:
Searches will be tailored based on available context rather than using generic queries:

- **With company context**: "John Smith" + "Goldman Sachs" + "Executive"
- **With location context**: "John Smith" + "New York" + "CEO"
- **With industry context**: "John Smith" + "Technology" + "Startup"

**Progressive Search Refinement**:

- Start with highly specific queries using all available context
- Gradually broaden search terms if initial queries yield insufficient results
- Stop searching when reliable information found or search quota exceeded

**Negative Result Recognition**:

- Cache unsuccessful search attempts to avoid repeating expensive queries
- Recognize when common names require additional context for meaningful results
- Flag cases where research is unlikely to yield actionable information

### Component 3: Information Validation Framework

#### Multi-Source Cross-Referencing

**Consensus Building**:
The system will use a weighted consensus approach when multiple sources provide conflicting information:

- **Source reliability weighting**: SEC filings weighted higher than social media
- **Recency preference**: More recent information preferred for current status
- **Corroboration bonus**: Information confirmed by multiple independent sources receives higher confidence

**Contradiction Detection**:
The system will actively identify contradictory information across sources:

- **Temporal impossibilities**: Birth dates that don't align with career timelines
- **Geographic conflicts**: Simultaneous presence in different locations
- **Professional inconsistencies**: Career roles that don't follow logical progression

#### Information Quality Scoring

**Confidence Calculation Framework**:
Each piece of extracted information will receive a confidence score based on:

- **Source authority** (SEC filing = 0.95, LinkedIn = 0.80, blog post = 0.30)
- **Information specificity** (exact date = higher than approximate)
- **Corroboration level** (confirmed by multiple sources = higher confidence)
- **Extraction certainty** (structured data = higher than inferred information)

**Quality Thresholds**:

- **High confidence**: >0.85 (suitable for automated decision enhancement)
- **Medium confidence**: 0.60-0.85 (flagged for human review)
- **Low confidence**: <0.60 (logged but not used for decision making)

#### Temporal Consistency Validation

- Career timeline logic: Education align with professional roles
- Age consistency: Professional achievements align with plausible ages
- Date normalization: Standard formats for cross-reference

### Component 4: Integration with Core Matching System

#### Enhanced Matching Pipeline

**Conditional Research Activation**:
Research will only be triggered when the initial matching system indicates potential value. This will be the enhanced pipeline:

1. **Initial screening** produces ambiguous result (40-80% confidence)
2. **Gap analysis** identifies specific missing information types
3. **Research orchestrator** executes targeted searches based on gaps
4. **Information validator** processes and validates findings
5. **Enhanced matcher** re-evaluates with enriched biographical context

**Confidence Score Integration**:
Enriched information will be integrated into the matching confidence calculation:

- **Supporting evidence**: Biographical alignment increases match confidence
- **Contradictory evidence**: Inconsistencies decrease match confidence
- **Information quality weighting**: Higher-quality sources have greater impact on confidence adjustment

#### Decision Enhancement Logic

**Positive Reinforcement**:
When enriched biographical data supports a potential match:

- **Age alignment**: Article age references match calculated age from birth date
- **Occupational consistency**: Professional background aligns with article context
- **Geographic coherence**: Location history consistent with article geography

**Negative Evidence Processing**:
When enriched data contradicts a potential match:

- **Age inconsistency**: Significant discrepancy between article age and calculated age
- **Professional contradiction**: Career background incompatible with article context
- **Geographic impossibility**: Location history incompatible with article events

### Performance Monitoring and Optimization

#### Key Performance Indicators

**Research Effectiveness Metrics**:

- **Information completion rate**: Percentage of cases successfully enriched with biographical data
- **Disambiguation success rate**: Percentage of ambiguous cases resolved through research
- **Source hit rate**: Success rate for different source types in providing useful information
- **Research time efficiency**: Average time required for information extraction per case

**Business Impact Metrics**:

- **False positive reduction**: Decrease in false positives attributable to enriched information
- **Analyst time savings**: Reduction in manual research time per case
- **Decision confidence improvement**: Average increase in matching confidence scores
- **Regulatory compliance score**: Percentage of cases with complete audit trails

#### Continuous Improvement Framework

**Machine Learning Integration**:
Over time, the system will learn from analyst feedback and research outcomes:

- **Source effectiveness modeling**: Predict which sources are most likely to contain useful information
- **Query optimization**: Improve search query formulation based on successful searches
- **Information prioritization**: Learn which types of biographical data are most valuable for disambiguation

**Feedback Loop Implementation**:

- **Analyst feedback collection**: Systematic collection of corrections and improvements from human analysts
- **Research outcome tracking**: Monitor long-term accuracy of enriched matching decisions
- **Source reliability updating**: Adjust source reliability scores based on information accuracy over time

### Important Note: Regulatory Compliance

**Audit Trail Documentation**:
Every research activity will be comprehensively logged:

- **Search queries executed**: Exact terms and sources queried
- **Information extracted**: Specific biographical data points found
- **Source attribution**: URLs and timestamps for all information sources
- **Confidence assessments**: Scoring rationale for each data point
- **Decision impact**: How enriched information affected final matching decision

**Explainability Requirements**:
All enriched information should include full attribution for analyst review:

- **Source identification**: Specific source and date of information extraction
- **Extraction method**: How biographical data was identified and extracted
- **Confidence rationale**: Factors contributing to information confidence score
- **Cross-reference status**: Whether information was corroborated by other sources
