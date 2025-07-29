import pytest
import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from main import app

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

client = TestClient(app)


def test_foreign_language_article():
    """Test handling of foreign language articles."""
    test_data = {
        "candidate": {"name": "Maria Garcia"},
        "article": "María García, la empresaria local, anunció su retiro hoy. La señora García ha sido una figura prominente en la comunidad."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 60


def test_title_and_honorifics():
    """Test matching with titles and honorifics."""
    test_data = {
        "candidate": {"name": "Elizabeth Johnson"},
        "article": "Dr. Elizabeth Johnson, PhD, was awarded the Nobel Prize for her groundbreaking research."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 80


def test_married_name_variations():
    """Test married name variations."""
    test_data = {
        "candidate": {"name": "Sarah Wilson"},
        "article": "Sarah Wilson-Jones, formerly Sarah Wilson, spoke at the conference about her new book."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 60


def test_company_affiliation_conflict():
    """Test company affiliation conflicts."""
    test_data = {
        "candidate": {
            "name": "Michael Brown",
            "occupation": "CEO at TechCorp"
        },
        "article": "Michael Brown, the CFO at FinanceInc, was arrested for fraud."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    if result["decision"] == "match":
        penalty = result["details"]["stage1"]["penalty"]
        assert penalty > 0
    else:
        assert result["decision"] == "no_match"


def test_location_conflict():
    """Test location-based conflicts."""
    test_data = {
        "candidate": {
            "name": "Jennifer Lee",
            "occupation": "Professor"
        },
        "article": "Jennifer Lee, a professor at Stanford University, was mentioned in the article. However, our candidate works at MIT."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    if result["stage"] == 2:
        assert result["confidence"] is not None
    else:
        assert result["decision"] in ["match", "no_match"]


def test_temporal_conflict():
    """Test temporal conflicts (different time periods)."""
    test_data = {
        "candidate": {
            "name": "Robert Davis",
            "dob": "1990-01-01"
        },
        "article": "Robert Davis, a veteran of World War II, passed away at the age of 95."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    if result["decision"] == "match":
        penalty = result["details"]["stage1"]["penalty"]
        assert penalty > 0, f"Expected penalty > 0, got {penalty}. Conflicts should be detected."
    else:
        assert result["decision"] == "no_match"


def test_ambiguous_references():
    """Test ambiguous pronoun references."""
    test_data = {
        "candidate": {"name": "David Wilson"},
        "article": "The CEO announced his resignation. He will be replaced by David Wilson. He has been with the company for 15 years."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 70


def test_negative_case_different_person():
    """Test clear negative case with different person."""
    test_data = {
        "candidate": {"name": "Alice Johnson"},
        "article": "Bob Smith was arrested yesterday for speeding. The incident occurred on Main Street."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "no_match"
    assert result["score"] < 60


def test_edge_case_single_letter():
    """Test edge case with single letter names."""
    test_data = {
        "candidate": {"name": "J Smith"},
        "article": "J. Smith was mentioned in the report."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 80


def test_case_sensitivity():
    """Test case sensitivity handling."""
    test_data = {
        "candidate": {"name": "Mary Johnson"},
        "article": "MARY JOHNSON was elected as the new mayor."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 90


def test_special_characters():
    """Test handling of special characters in names."""
    test_data = {
        "candidate": {"name": "José María García"},
        "article": "Jose Maria Garcia was appointed as the new director."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 70


def test_false_positive_prevention():
    """Test prevention of false positives with unrelated names."""
    test_data = {
        "candidate": {"name": "Megan"},
        "article": "Michael Tanner, the U.S. Attorney, announced the indictment today."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    assert result["decision"] == "no_match", f"Expected no_match, got {result['decision']} with score {result['score']}"
    assert result["score"] < 60, f"Expected score < 60, got {result['score']}"
    
    stage1_details = result["details"]["stage1"]
    assert "all_variants" in stage1_details, "Name variants should be included in Stage 1 results"
    assert "megan" in stage1_details["all_variants"], "Original name should be in variants"


def test_substring_name_prevention():
    """Test prevention of false positives with substring names."""
    test_data = {
        "candidate": {"name": "Mora"},
        "article": "Alex Morales was appointed as the new director of the company."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    assert result["decision"] == "no_match", f"Expected no_match, got {result['decision']} with score {result['score']}"
    assert result["score"] < 60, f"Expected score < 60, got {result['score']}"
    
    stage1_details = result["details"]["stage1"]
    assert "all_variants" in stage1_details, "Name variants should be included"
    assert "mora" in stage1_details["all_variants"], "Original name should be in variants"

def test_occupation_conflict_detection():
    """Test that occupation conflicts are properly detected and prevent false matches."""
    test_data = {
        "candidate": {
            "name": "Alex",
            "occupation": "Judge"
        },
        "article": "Dr. Alex performed surgery on the patient yesterday. The medical procedure was successful."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    print(f"Occupation conflict test result: {result}")
    
    stage1_details = result["details"]["stage1"]
    assert stage1_details["penalty"] > 0, f"Expected penalty > 0, got {stage1_details['penalty']}"
    
    if result["stage"] == 1:
        assert result["decision"] != "match", "Should not be a clear match with occupation conflict"
    else:
        assert "occupation" in result["explanation"].lower() or "conflict" in result["explanation"].lower(), "Should mention occupation conflict"
    
    assert "all_variants" in stage1_details, "Name variants should be included"
    assert "alex" in stage1_details["all_variants"], "Original name should be in variants"


def test_occupation_conflict_with_multiple_people():
    """Test occupation conflict detection when there are multiple people in the article."""
    test_data = {
        "candidate": {
            "name": "Alex",
            "occupation": "Judge"
        },
        "article": "Dr. Alex performed surgery on the patient yesterday. Judge Smith presided over the court case. The medical procedure was successful."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    print(f"Multiple people occupation conflict test result: {result}")
    
    stage1_details = result["details"]["stage1"]
    assert stage1_details["penalty"] > 0, f"Expected penalty > 0, got {stage1_details['penalty']}"
    
    if result["stage"] == 1:
        assert result["decision"] != "match", "Should not be a clear match with occupation conflict"
    else:
        assert "occupation" in result["explanation"].lower() or "conflict" in result["explanation"].lower(), "Should mention occupation conflict"
    
    assert "all_variants" in stage1_details, "Name variants should be included"
    assert "alex" in stage1_details["all_variants"], "Original name should be in variants"


if __name__ == "__main__":
    pytest.main([__file__]) 