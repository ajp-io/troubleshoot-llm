from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import re
from typing import Dict, List, Tuple

# Load a model suitable for text classification
MODEL_NAME = "microsoft/deberta-v3-base"  # Better for understanding technical text
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# Common error patterns and their potential causes for Kubernetes/Helm/KOTS
ERROR_PATTERNS = {
    # Helm specific errors
    r"helm.*release.*failed": "Helm release installation or upgrade failed",
    r"chart.*requires.*kubernetes.*version": "Kubernetes version compatibility issue",
    r"failed.*to.*install.*chart": "Chart installation failure",
    r"helm.*upgrade.*failed": "Helm upgrade failure",
    r"chart.*not.*found": "Chart not found in repository",
    
    # KOTS specific errors
    r"kots.*install.*failed": "KOTS installation failure",
    r"kots.*upgrade.*failed": "KOTS upgrade failure",
    r"kots.*version.*incompatible": "KOTS version compatibility issue",
    r"kots.*config.*invalid": "Invalid KOTS configuration",
    r"kots.*license.*invalid": "Invalid or expired KOTS license",
    
    # Kubernetes common errors
    r"image.*pull.*failed": "Container image pull failure",
    r"pod.*crash.*loop": "Pod crash loop detected",
    r"insufficient.*cpu|insufficient.*memory": "Resource constraints",
    r"persistentvolumeclaim.*not.*found": "Storage/PVC issue",
    r"service.*not.*found": "Service discovery issue",
    r"configmap.*not.*found": "Configuration issue",
    r"secret.*not.*found": "Secret/credential issue",
    r"node.*not.*ready": "Node health issue",
    r"network.*policy.*denied": "Network policy restriction",
    r"rbac.*forbidden": "RBAC permission issue",
    
    # Common infrastructure errors
    r"connection.*refused": "Network connectivity issue",
    r"permission.*denied": "Access control or permissions issue",
    r"timeout": "Resource exhaustion or network latency",
    r"out of memory": "Resource exhaustion",
    r"not found": "Missing resource or configuration",
    r"already exists": "Resource conflict",
    r"invalid.*format": "Data format or syntax error",
    r"authentication.*failed": "Credentials or authentication issue",
    r"dependency.*missing": "Missing dependency or package",
    r"port.*in use": "Resource conflict - port already in use"
}

def extract_error_context(text: str) -> List[str]:
    """Extract relevant error messages and their context."""
    # Split by common delimiters and filter out empty lines
    lines = [line.strip() for line in re.split(r'[\n\r]+', text) if line.strip()]
    
    # Find lines containing error indicators
    error_lines = []
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'fatal', 'critical', 'warning']):
            # Get context (2 lines before and after)
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            context = lines[start:end]
            error_lines.extend(context)
    
    return error_lines if error_lines else lines

def identify_patterns(text: str) -> List[Tuple[str, str]]:
    """Identify common error patterns and their potential causes."""
    matches = []
    for pattern, cause in ERROR_PATTERNS.items():
        if re.search(pattern, text.lower()):
            matches.append((pattern, cause))
    return matches

def get_next_steps(root_cause: str) -> List[str]:
    """Generate next steps based on the root cause."""
    if "helm" in root_cause.lower():
        return [
            "Check Helm chart version compatibility",
            "Verify Helm repository access",
            "Review Helm values and configuration",
            "Check Kubernetes version requirements"
        ]
    elif "kots" in root_cause.lower():
        return [
            "Verify KOTS license validity",
            "Check KOTS version compatibility",
            "Review KOTS configuration",
            "Check application requirements"
        ]
    elif "kubernetes" in root_cause.lower():
        return [
            "Check Kubernetes cluster health",
            "Verify resource availability",
            "Review pod and service status",
            "Check network policies"
        ]
    elif "network" in root_cause.lower():
        return [
            "Check network connectivity",
            "Verify firewall settings",
            "Confirm service is running on the expected port",
            "Check network policies"
        ]
    elif "permission" in root_cause.lower():
        return [
            "Verify user permissions",
            "Check RBAC settings",
            "Review security contexts",
            "Check service account permissions"
        ]
    elif "resource" in root_cause.lower():
        return [
            "Check system resources (CPU, memory, disk)",
            "Review resource limits and quotas",
            "Consider scaling resources",
            "Check node capacity"
        ]
    else:
        return [
            "Review the error context for more details",
            "Check system logs for related errors",
            "Verify configuration settings",
            "Check application status"
        ]

def analyze_log(text: str) -> Dict[str, str]:
    """
    Analyze log text and return structured analysis.
    Returns a dictionary containing:
    - root_cause: Identified root cause
    - confidence: Confidence score
    - next_steps: Recommended next steps
    - context: Relevant error context
    """
    # Extract error context
    error_context = extract_error_context(text)
    context_text = "\n".join(error_context)
    
    # Identify common patterns
    pattern_matches = identify_patterns(text)
    
    # Prepare input for the model
    inputs = tokenizer(context_text, return_tensors="pt", truncation=True, max_length=512)
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Get model predictions
    probs = torch.nn.functional.softmax(outputs.logits, dim=1)
    confidence, prediction = torch.max(probs, dim=1)
    
    # Determine root cause based on patterns and model output
    root_cause = "Unknown issue"
    if pattern_matches:
        # Prioritize Helm and KOTS specific issues
        helm_kots_matches = [m for m in pattern_matches if any(x in m[1].lower() for x in ['helm', 'kots'])]
        if helm_kots_matches:
            root_cause = helm_kots_matches[0][1]
        else:
            root_cause = pattern_matches[0][1]
    
    # Generate next steps based on the root cause
    next_steps = get_next_steps(root_cause)
    
    return {
        "root_cause": root_cause,
        "confidence": f"{confidence.item():.2f}",
        "next_steps": next_steps,
        "context": context_text
    }
