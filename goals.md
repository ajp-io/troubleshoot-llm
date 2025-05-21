# Goal

Build a proof-of-concept REST API that uses a pre-trained DistilBERT model to analyze log messages or error text and return a meaningful interpretation.

The purpose is to validate whether a local CPU-friendly language model can be used to assist with troubleshooting in a product like Replicated.

Key requirements:
- Runs on CPU (no GPU dependency)
- Accepts log data via HTTP POST
- Returns a high-quality interpretation, identifying possible root causes or helpful troubleshooting suggestions
- Containerized for easy use and deployment
- Output should be accurate enough to be helpful for real-world debugging, not just mocked or dummy data

Model does not need to be fine-tuned for now, but prompt engineering or simple logic should be applied to improve response quality.
