#!/bin/bash

# Streamlit Frontend 실행 스크립트

echo "🎨 Starting Streamlit Frontend..."
echo "📍 Server will be available at: http://localhost:8501"
echo ""

cd "$(dirname "$0")"
streamlit run frontend/app.py
