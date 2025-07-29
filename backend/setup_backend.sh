#!/bin/bash

# MIT License
# Copyright (c) 2024 Media Screening Tool

echo "🔧 Setting up backend dependencies..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or later."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

echo "🤖 Installing spaCy models..."
python3 -m spacy download en_core_web_sm
python3 -m spacy download xx_ent_wiki_sm

echo "✅ Backend setup complete!"
echo ""
echo "🧪 You can now run tests with:"
echo "   cd backend"
echo "   python test_api.py"
echo "   python test_llm.py"
echo "   python test_stage2.py" 