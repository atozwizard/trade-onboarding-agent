#!/bin/bash

# FastAPI Backend 실행 스크립트

echo "🚀 Starting FastAPI Backend..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""

cd "$(dirname "$0")"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
