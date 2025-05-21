# Tasks

## 🛠️ Setup Environment
- [ ] Create `requirements.txt` with required Python libraries

## 🧠 Load the Model
- [ ] Load DistilBERT using Hugging Face
- [ ] Add a function `analyze_log(text: str) -> str` that:
  - Tokenizes the text
  - Runs it through the model
  - Extracts meaningful interpretation from outputs

## 🌐 Build the API Server
- [ ] Use FastAPI to expose a POST `/analyze` endpoint
- [ ] Accept input as JSON: `{ "log": "..." }`
- [ ] Return a JSON response: `{ "analysis": "..." }`

## 🧪 Test Input
- [ ] Create a realistic test input JSON file

## 🐳 Dockerize
- [ ] Create a Dockerfile to containerize the app

## 🔍 Accuracy Improvements
- [ ] Add simple rule-based heuristics for common patterns
- [ ] Template output to improve clarity
