import spacy
import re
import csv
import os
from typing import List, Tuple, Optional, Dict
from rapidfuzz import fuzz
from models import Candidate, Stage1Result


def extract_context_around_person(text: str, person_name: str, window: int = 200) -> str:
    """Extract context around the best matching person."""
    match = re.search(re.escape(person_name), text, re.IGNORECASE)
    if not match:
        return text[:window]
    
    start = match.start()
    end = match.end()
    
    context_start = max(0, start - window // 2)
    context_end = min(len(text), end + window // 2)
    
    return text[context_start:context_end]

try:
    nlp = spacy.load("en_core_web_sm")
    print("✅ Loaded English spaCy model (small)")
except OSError:
    try:
        nlp = spacy.load("en_core_web_md")
        print("✅ Loaded English spaCy model (medium)")
    except OSError:
        try:
            nlp = spacy.load("xx_ent_wiki_sm")
            print("✅ Loaded multilingual spaCy model")
        except OSError:
            print("❌ No spaCy models found. Please install them with:")
            print("   python -m spacy download en_core_web_sm")
            print("   python -m spacy download xx_ent_wiki_sm")
            print("   Or run: ./setup_backend.sh")
            raise OSError("spaCy models not installed. Please run setup_backend.sh")

def load_nicknames() -> Dict[str, List[str]]:
    """Load nicknames from the CSV file."""
    nicknames = {}
    csv_path = os.path.join(os.path.dirname(__file__), "data", "names.csv")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['relationship'] == 'has_nickname':
                    full_name = row['name1'].lower().strip()
                    nickname = row['name2'].lower().strip()
                    
                    if full_name not in nicknames:
                        nicknames[full_name] = []
                    nicknames[full_name].append(nickname)
    except FileNotFoundError:
        print(f"Warning: names.csv not found at {csv_path}, using fallback nicknames")
        nicknames = {
            "william": ["bill", "billy", "will", "willy"],
            "robert": ["bob", "rob", "robby", "bobby"],
            "michael": ["mike", "mikey", "mick", "mickey"],
            "james": ["jim", "jimmy", "jamie"],
            "david": ["dave", "davey"],
            "richard": ["rick", "ricky", "dick", "dickie"],
            "thomas": ["tom", "tommy"],
            "christopher": ["chris", "topher"],
            "daniel": ["dan", "danny"],
            "matthew": ["matt", "matty"],
            "elizabeth": ["liz", "lizzy", "beth", "betty", "lisa"],
            "sarah": ["sally", "sadie"],
            "margaret": ["maggie", "meg", "peggy"],
            "jennifer": ["jen", "jenny"],
            "jessica": ["jess", "jessie"],
            "ashley": ["ash"],
            "emily": ["em", "emmy"],
            "samantha": ["sam", "sammy"],
            "stephanie": ["steph", "stephie"],
            "nicole": ["nikki", "nic"],
        }
    except Exception as e:
        print(f"Error loading nicknames from CSV: {e}")
        return {}
    
    return nicknames

NICKNAMES = load_nicknames()


def generate_name_variants(name: str) -> List[str]:
    """Generate various name variants for fuzzy matching."""
    variants = [name.lower().strip()]
    
    parts = name.lower().split()
    if len(parts) >= 2:
        # Initials
        initials = " ".join(part[0] + "." for part in parts)
        variants.append(initials)
        initials_no_space = "".join(part[0] + "." for part in parts[:-1]) + parts[-1]
        variants.append(initials_no_space)
        
        # Last name first
        variants.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
        
        if len(parts) >= 3:
            for i in range(1, len(parts) - 1):
                middle_as_first = " ".join(parts[i:])
                variants.append(middle_as_first)
                variants.append(f"{parts[-1]}, {' '.join(parts[i:-1])}")
        
        for part in parts:
            if part in NICKNAMES:
                for nickname in NICKNAMES[part]:
                    new_parts = parts.copy()
                    new_parts[new_parts.index(part)] = nickname
                    variants.append(" ".join(new_parts))
        
        if len(parts) >= 3:
            variants.append(f"{parts[1]} {parts[-1]}")  # Middle + Last
            variants.append(f"{parts[-1]} {parts[1]}")  # Last + Middle
        
        if len(parts) >= 3:
            # First + Last (skip middle)
            variants.append(f"{parts[0]} {parts[-1]}")
            # Middle + Last
            if len(parts) > 2:
                variants.append(f"{parts[1]} {parts[-1]}")
    
    clean_name = re.sub(r'[^\w\s]', '', name.lower())
    if clean_name != name.lower():
        variants.append(clean_name)
    
    if len(parts) == 1:
        variants.append(parts[0])
    
    return list(set(variants))


def extract_person_entities(text: str) -> List[str]:
    """Extract all PERSON entities from text using spaCy."""
    doc = nlp(text)
    persons = []
    
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            persons.append(ent.text.strip())
    
    if not persons:
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # First Middle Last
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # First Middle Middle Last
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                non_name_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                words = match.split()
                if not any(word.lower() in non_name_words for word in words):
                    persons.append(match)
    
    return list(set(persons))


def check_attribute_conflicts(candidate: Candidate, text: str, best_person: str) -> Tuple[int, str]:
    """Check for DOB and occupation conflicts."""
    penalty = 0
    explanation = ""
    
    if candidate.dob:
        try:
            from datetime import datetime
            dob_year = int(candidate.dob[:4])
            
            age_patterns = [
                r'(\d{1,2})\s*(?:years?\s*old|yo|year-old|years?-old|year\s*old|-year-old)', 
                r'age\s*of\s*(\d{1,2})',  
                r'(\d{1,2})\s*yo',  
                r'(\d{1,2})\s*years?', 
            ]
            
            all_age_matches = []
            for pattern in age_patterns:
                matches = re.findall(pattern, text.lower())
                all_age_matches.extend(matches)
            
            print(f"All age matches: {all_age_matches}") 
            
            for age_match in all_age_matches:
                age = int(age_match)
                current_year = datetime.now().year
                article_year = current_year - age
                
                if abs(article_year - dob_year) >= 2:
                    penalty += 30
                    explanation += f"DOB conflict: candidate born {dob_year}, article suggests {article_year}. "
                    break
            
        except (ValueError, IndexError) as e:
            pass
    
    if candidate.occupation:
        occupation_words = set(candidate.occupation.lower().split())
        
        person_context = extract_context_around_person(text, best_person, window=200)
        context_words = set(person_context.lower().split())
        
        occupation_in_context = any(word in context_words for word in occupation_words if len(word) > 2)
        
        occupation_indicators = {
            "doctor": ["physician", "surgeon", "medical", "hospital", "clinic", "patient", "treatment", "dr.", "dr "],
            "judge": ["court", "trial", "legal", "lawyer", "attorney", "prosecutor", "defendant", "judge", "judicial"],
            "lawyer": ["attorney", "legal", "court", "trial", "law", "client", "case", "lawyer"],
            "teacher": ["school", "education", "student", "classroom", "university", "professor", "teacher"],
            "engineer": ["engineering", "technical", "construction", "design", "project", "engineer"],
            "manager": ["management", "executive", "director", "supervisor", "leadership", "manager"],
            "police": ["officer", "law enforcement", "detective", "investigation", "arrest", "police"],
            "nurse": ["nursing", "medical", "hospital", "patient", "care", "healthcare", "nurse"]
        }
        
        candidate_occupation_lower = candidate.occupation.lower()
        conflicting_indicators = []
        
        for profession, indicators in occupation_indicators.items():
            if profession in candidate_occupation_lower:
                for indicator in indicators:
                    if indicator in person_context.lower():
                        conflicting_indicators.append(indicator)
                        break
                
        if conflicting_indicators:
            penalty += 40 
            explanation += f"Occupation conflict: candidate is '{candidate.occupation}' but context around '{best_person}' suggests different profession (found: {', '.join(conflicting_indicators)}). "
        elif not occupation_in_context:
            penalty += 20  
            explanation += f"Occupation '{candidate.occupation}' not found in context around '{best_person}'. "
    
    return penalty, explanation


def generate_stage1_reasons(decision: str, final_score: float, best_score: float, penalty: int, best_person: str, best_variant: str, conflict_explanation: str, candidate: Candidate) -> str:
    """Generate plain English explanation for Stage 1 decision."""
    
    if decision == "no_match":
        if final_score < 60:
            if best_person:
                return f"The best name match found was '{best_person}' with a similarity score of {best_score:.1f}%, which is below the 60% threshold. {conflict_explanation}"
            else:
                return "No person names found in the article that match the candidate."
        else:
            return f"Despite a good name match ({best_score:.1f}%), conflicts were detected: {conflict_explanation}"
    
    elif decision == "match":
        if best_variant != candidate.name:
            return f"Strong match found: '{best_person}' matches the candidate's name variant '{best_variant}' with {best_score:.1f}% similarity. No conflicts detected."
        else:
            return f"Strong match found: '{best_person}' matches the candidate's name '{candidate.name}' with {best_score:.1f}% similarity. No conflicts detected."
    
    else:  # review
        if penalty > 0:
            return f"Borderline case: '{best_person}' matches '{best_variant}' with {best_score:.1f}% similarity, but conflicts were detected: {conflict_explanation} Sending to Stage 2 for further analysis."
        else:
            return f"Borderline case: '{best_person}' matches '{best_variant}' with {best_score:.1f}% similarity, which is between 60-80%. Sending to Stage 2 for further analysis."


def stage1_filter(candidate: Candidate, article: str) -> Stage1Result:
    """Stage 1: Deterministic name filtering with fuzzy matching."""

    variants = generate_name_variants(candidate.name)
    print(f"Generated {len(variants)} name variants: {variants[:5]}...") 
    
    persons = extract_person_entities(article)
    print(f"Found {len(persons)} person entities: {persons[:5]}...")
    
    if not persons:
        return Stage1Result(
            decision="no_match",
            score=0,
            best_person="",
            candidate_variant=candidate.name,
            all_variants=", ".join(variants),
            penalty=0,
            reasons="No person names found in the article to compare against."
        )
    
    best_score = 0
    best_person = ""
    best_variant = candidate.name
    
    for variant in variants:
        for person in persons:
            score = fuzz.token_set_ratio(variant, person.lower())
            
            variant_parts = variant.split()
            person_parts = person.lower().split()
            
            if len(variant_parts) == 1 and len(person_parts) >= 2:
                if score < 85:
                    continue
            
            if len(variant_parts) == 1 and len(person_parts) == 1:
                if score < 70:
                    continue
            
            if score > best_score:
                best_score = score
                best_person = person
                best_variant = variant
    
    penalty, conflict_explanation = check_attribute_conflicts(candidate, article, best_person)
    final_score = max(0, best_score - penalty)
    
    if final_score < 60:
        decision = "no_match"
    elif final_score >= 80 and penalty == 0:
        decision = "match"
    else:
        decision = "review"
    
    reasons = generate_stage1_reasons(decision, final_score, best_score, penalty, best_person, best_variant, conflict_explanation, candidate)
    
    return Stage1Result(
        decision=decision,
        score=int(round(final_score)),
        best_person=best_person,
        candidate_variant=best_variant,
        all_variants=", ".join(variants),
        penalty=int(round(penalty)),
        reasons=reasons
    ) 
