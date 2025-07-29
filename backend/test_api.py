import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from main import app
from models import Candidate
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

client = TestClient(app)


@pytest.fixture
def positive_test_case():
    """Positive test case: article about Robert Johnson with nickname and correct occupation."""
    return {
        "candidate": {
            "name": "Robert Johnson",
            "dob": "1980-01-01", 
        },
        "article": """
        Tech startup founder Bob Johnson announced today that his company has secured 
        $5 million in funding. The software engineer, who founded the company in 2020, 
        has been developing innovative AI solutions. Johnson, born in 1980, has been 
        a leading figure in the local tech scene and is known for his work in machine learning.
        """
    }


@pytest.fixture
def negative_test_case():
    """Negative test case: article about different person with same name but different DOB."""
    return {
        "candidate": {
            "name": "John Smith",
            "dob": "1980-01-01",
        },
        "article": """
        Local software engineer John Smith was arrested yesterday for speeding. 
        The 25-year-old resident of Springfield was caught driving 85 mph in a 
        35 mph zone. Smith, who works at a local tech startup, was released on 
        bail and is scheduled to appear in court next month.
        """
    }


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_positive_match(positive_test_case):
    """Test that positive case results in a match."""
    response = client.post("/api/match", json=positive_test_case)
    assert response.status_code == 200
    
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 60
    explanation = result["explanation"].lower()
    assert "johnson" in explanation or "bob" in explanation or "robert" in explanation


def test_negative_match(negative_test_case):
    """Test that negative case results in no_match due to DOB conflict."""
    response = client.post("/api/match", json=negative_test_case)
    assert response.status_code == 200
    
    result = response.json()
    
    if result["decision"] == "match":
        penalty = result["details"]["stage1"]["penalty"]
        assert penalty > 0, f"Expected penalty > 0, got {penalty}"
    else:
        assert result["decision"] == "no_match"


def test_api_structure():
    """Test that API response has correct structure."""
    test_data = {
        "candidate": {
            "name": "Test Person",
            "dob": None,
            "occupation": None
        },
        "article": "This is a test article about Test Person."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    
    result = response.json()
    required_fields = ["decision", "stage", "score", "confidence", "explanation", "details"]
    for field in required_fields:
        assert field in result
    
    assert result["decision"] in ["match", "no_match"]
    assert result["stage"] in [1, 2]
    assert 0 <= result["score"] <= 100
    assert result["confidence"] is None or 0.0 <= result["confidence"] <= 1.0


def test_invalid_request():
    """Test handling of invalid request data."""
    invalid_data = {
        "candidate": {
        },
        "article": "Some article text"
    }
    
    response = client.post("/api/match", json=invalid_data)
    assert response.status_code == 422  
    

    invalid_data2 = {
        "candidate": {
            "name": ""
        },
        "article": "Some article text"
    }
    
    response2 = client.post("/api/match", json=invalid_data2)
    assert response2.status_code == 422 


def test_nickname_matching():
    """Test nickname expansion and matching."""
    test_data = {
        "candidate": {"name": "William Johnson"},
        "article": "Bill Johnson, the local entrepreneur, announced his retirement today."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 80
    
    stage1_details = result["details"]["stage1"]
    assert "all_variants" in stage1_details, "Name variants should be included"
    assert "bill johnson" in stage1_details["all_variants"].lower(), "Nickname should be in variants"


def test_initials_matching():
    """Test matching with initials."""
    test_data = {
        "candidate": {"name": "Michael David Smith"},
        "article": "M.D. Smith was appointed as the new CEO of the company. The board unanimously approved the appointment."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    if result["stage"] == 1:
        assert result["decision"] == "match"
        assert result["score"] >= 60
    else:
        assert result["decision"] in ["match", "no_match"]
        assert result["score"] >= 60


def test_initials_matching_simple():
    """Test matching with initials - simpler case."""
    test_data = {
        "candidate": {"name": "John Smith"},
        "article": "J. Smith attended the meeting."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 60


def test_last_name_first():
    """Test matching with last name first format."""
    test_data = {
        "candidate": {"name": "Sarah Elizabeth Wilson"},
        "article": "Wilson, Sarah was seen at the charity event last night."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 70


def test_middle_name_as_given():
    """Test using middle name as given name."""
    test_data = {
        "candidate": {"name": "John Michael Davis"},
        "article": "Michael Davis, the renowned architect, designed the new museum."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 70


def test_occupation_conflict():
    """Test occupation conflict detection."""
    test_data = {
        "candidate": {
            "name": "Robert Chen",
            "occupation": "Software Engineer"
        },
        "article": "Robert Chen, a local lawyer, was elected to the city council."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    if result["decision"] == "match":
        penalty = result["details"]["stage1"]["penalty"]
        assert penalty > 0
    else:
        assert result["decision"] == "no_match"


def test_no_person_entities():
    """Test case where no person entities are found."""
    test_data = {
        "candidate": {"name": "Alice Johnson"},
        "article": "The weather today is sunny with a high of 75 degrees."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "no_match"
    assert result["score"] == 0


def test_partial_name_match():
    """Test partial name matching."""
    test_data = {
        "candidate": {"name": "Christopher Thompson"},
        "article": "Chris Thompson was spotted at the restaurant."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 70


def test_cultural_name_variations():
    """Test cultural name variations."""
    test_data = {
        "candidate": {"name": "Li Wei Chen"},
        "article": "Wei Chen, the mathematician, published a groundbreaking paper."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 60


def test_mononym_matching():
    """Test matching with mononyms."""
    test_data = {
        "candidate": {"name": "Madonna"},
        "article": "Madonna performed at the Super Bowl halftime show."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "match"
    assert result["score"] >= 90


def test_stage2_trigger():
    """Test that Stage 2 is triggered for borderline cases."""
    test_data = {
        "candidate": {
            "name": "David Wilson",
            "occupation": "Teacher"
        },
        "article": "David Wilson, a local educator, was mentioned in passing during the school board meeting."
    }
    
    response = client.post("/api/match", json=test_data)
    assert response.status_code == 200
    result = response.json()
    
    assert result["stage"] == 2
    assert result["confidence"] is not None
    assert 0.0 <= result["confidence"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__]) 