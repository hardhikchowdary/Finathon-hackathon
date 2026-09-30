# Dynamic Skill Graph MVP

## Prerequisites
- Node.js 18+
- Python 3.11+
- Anthropic API Key (optional)

## Setup Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# To run
uvicorn app.main:app --reload
```

## Setup Frontend
```bash
cd frontend
npm install
npm install react-router-dom @tanstack/react-query react-cytoscapejs cytoscape recharts lucide-react clsx tailwind-merge
# Tailwind setup done separately
npm run dev
```