from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from model_loader import analyze_log
from typing import List, Optional, Dict
import os
import glob
from datetime import datetime, timedelta
import subprocess
import json

app = FastAPI(
    title="KOTS and Helm Log Analyzer",
    description="API for analyzing KOTS and Helm logs using DistilBERT",
    version="1.0.0"
)

class AnalysisResponse(BaseModel):
    root_cause: str
    confidence: str
    next_steps: List[str]
    context: str
    timestamp: Optional[str] = None

class LogFileResponse(BaseModel):
    filename: str
    analysis: AnalysisResponse

class ConsolidatedAnalysisResponse(BaseModel):
    critical_issues: List[Dict]
    warnings: List[Dict]
    system_status: Dict
    log_sources_analyzed: List[str]
    timestamp: str

def get_journalctl_logs(service: str, hours: int = 24) -> str:
    """Get logs from journalctl for a specific service."""
    try:
        result = subprocess.run(
            ["journalctl", "--since", f"{hours} hours ago", "--no-pager", "-u", service],
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error getting journalctl logs: {str(e)}"

def get_pod_logs(log_dir: str, namespace: Optional[str] = None, pod_name: Optional[str] = None, hours: int = 24) -> List[LogFileResponse]:
    """Get and analyze pod logs from containerd directory."""
    results = []
    if not os.path.exists(log_dir):
        return results
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    # Construct the search pattern based on namespace and pod name filters
    search_pattern = log_dir
    if namespace:
        search_pattern = os.path.join(search_pattern, f"{namespace}_*")
    if pod_name:
        search_pattern = os.path.join(search_pattern, f"*_{pod_name}_*")
    search_pattern = os.path.join(search_pattern, "*.log")
    
    for log_file in glob.glob(search_pattern, recursive=True):
        if os.path.getmtime(log_file) >= cutoff_time.timestamp():
            try:
                with open(log_file, 'r') as f:
                    log_text = f.read()
                    result = analyze_log(log_text)
                    result["timestamp"] = datetime.fromtimestamp(os.path.getmtime(log_file)).isoformat()
                    
                    # Extract pod info from the path
                    path_parts = log_file.split('/')
                    pod_info = path_parts[-2] if len(path_parts) > 1 else "unknown"
                    
                    results.append({
                        "filename": f"{pod_info}/{os.path.basename(log_file)}",
                        "analysis": result
                    })
            except Exception as e:
                print(f"Error reading log file {log_file}: {str(e)}")
    
    return results

@app.get("/analyze/embedded-cluster", response_model=List[LogFileResponse])
async def analyze_embedded_cluster_logs(hours: int = 24):
    """
    Analyze logs from the embedded-cluster installation.
    Returns analysis of all log files from the specified time period.
    """
    try:
        results = []
        
        # Check /var/log/embedded-cluster
        log_dir = "/logs/embedded-cluster"
        if os.path.exists(log_dir):
            for log_file in glob.glob(f"{log_dir}/*.log"):
                if os.path.getmtime(log_file) >= (datetime.now() - timedelta(hours=hours)).timestamp():
                    with open(log_file, 'r') as f:
                        log_text = f.read()
                        result = analyze_log(log_text)
                        result["timestamp"] = datetime.fromtimestamp(os.path.getmtime(log_file)).isoformat()
                        results.append({
                            "filename": os.path.basename(log_file),
                            "analysis": result
                        })
        
        # Check /var/lib/embedded-cluster/logs
        data_log_dir = "/logs/embedded-cluster-data/logs"
        if os.path.exists(data_log_dir):
            for log_file in glob.glob(f"{data_log_dir}/*.log"):
                if os.path.getmtime(log_file) >= (datetime.now() - timedelta(hours=hours)).timestamp():
                    with open(log_file, 'r') as f:
                        log_text = f.read()
                        result = analyze_log(log_text)
                        result["timestamp"] = datetime.fromtimestamp(os.path.getmtime(log_file)).isoformat()
                        results.append({
                            "filename": os.path.basename(log_file),
                            "analysis": result
                        })
        
        # Get systemd service logs
        services = ["k0scontroller.service", "k0sworker.service", "local-artifact-mirror.service"]
        for service in services:
            log_text = get_journalctl_logs(service, hours)
            if log_text:
                result = analyze_log(log_text)
                result["timestamp"] = datetime.now().isoformat()
                results.append({
                    "filename": f"journalctl-{service}",
                    "analysis": result
                })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing embedded-cluster logs: {str(e)}")

@app.get("/analyze/pod-logs", response_model=List[LogFileResponse])
async def analyze_pod_logs(namespace: Optional[str] = None, pod_name: Optional[str] = None, hours: int = 24):
    """
    Analyze pod logs from containerd directory.
    Returns analysis of all pod log files from the specified time period.
    Optional filters for namespace and pod name.
    """
    try:
        return get_pod_logs("/logs/pods", namespace, pod_name, hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing pod logs: {str(e)}")

@app.get("/analyze/syslog", response_model=LogFileResponse)
async def analyze_syslog(hours: int = 24):
    """
    Analyze system logs from syslog.
    """
    try:
        syslog_path = "/logs/syslog"
        if not os.path.exists(syslog_path):
            raise HTTPException(status_code=404, detail="Syslog file not found")
        
        with open(syslog_path, 'r') as f:
            log_text = f.read()
            result = analyze_log(log_text)
            result["timestamp"] = datetime.fromtimestamp(os.path.getmtime(syslog_path)).isoformat()
            return {
                "filename": "syslog",
                "analysis": result
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing syslog: {str(e)}")

@app.get("/analyze/all", response_model=ConsolidatedAnalysisResponse)
async def analyze_all_logs(hours: int = 24):
    """
    Analyze all available log sources and provide a consolidated view of issues.
    Returns critical issues, warnings, and system status from all log sources.
    """
    try:
        critical_issues = []
        warnings = []
        analyzed_sources = []
        
        # 1. Analyze embedded-cluster logs
        embedded_logs = await analyze_embedded_cluster_logs(hours)
        if embedded_logs:
            analyzed_sources.append("embedded-cluster")
            for log in embedded_logs:
                if "error" in log["analysis"]["root_cause"].lower() or "fail" in log["analysis"]["root_cause"].lower():
                    critical_issues.append({
                        "source": "embedded-cluster",
                        "file": log["filename"],
                        "issue": log["analysis"]["root_cause"],
                        "confidence": log["analysis"]["confidence"],
                        "next_steps": log["analysis"]["next_steps"],
                        "context": log["analysis"]["context"]
                    })
                else:
                    warnings.append({
                        "source": "embedded-cluster",
                        "file": log["filename"],
                        "issue": log["analysis"]["root_cause"],
                        "confidence": log["analysis"]["confidence"],
                        "next_steps": log["analysis"]["next_steps"]
                    })
        
        # 2. Analyze pod logs
        pod_logs = await analyze_pod_logs(hours=hours)
        if pod_logs:
            analyzed_sources.append("pods")
            for log in pod_logs:
                if "error" in log["analysis"]["root_cause"].lower() or "fail" in log["analysis"]["root_cause"].lower():
                    critical_issues.append({
                        "source": "pods",
                        "file": log["filename"],
                        "issue": log["analysis"]["root_cause"],
                        "confidence": log["analysis"]["confidence"],
                        "next_steps": log["analysis"]["next_steps"],
                        "context": log["analysis"]["context"]
                    })
                else:
                    warnings.append({
                        "source": "pods",
                        "file": log["filename"],
                        "issue": log["analysis"]["root_cause"],
                        "confidence": log["analysis"]["confidence"],
                        "next_steps": log["analysis"]["next_steps"]
                    })
        
        # 3. Analyze syslog
        try:
            syslog = await analyze_syslog(hours)
            analyzed_sources.append("syslog")
            if "error" in syslog["analysis"]["root_cause"].lower() or "fail" in syslog["analysis"]["root_cause"].lower():
                critical_issues.append({
                    "source": "syslog",
                    "file": syslog["filename"],
                    "issue": syslog["analysis"]["root_cause"],
                    "confidence": syslog["analysis"]["confidence"],
                    "next_steps": syslog["analysis"]["next_steps"],
                    "context": syslog["analysis"]["context"]
                })
            else:
                warnings.append({
                    "source": "syslog",
                    "file": syslog["filename"],
                    "issue": syslog["analysis"]["root_cause"],
                    "confidence": syslog["analysis"]["confidence"],
                    "next_steps": syslog["analysis"]["next_steps"]
                })
        except HTTPException:
            # Syslog might not be available, that's okay
            pass
        
        # Determine overall system status
        system_status = {
            "status": "healthy" if not critical_issues else "unhealthy",
            "critical_issues_count": len(critical_issues),
            "warnings_count": len(warnings),
            "log_sources_available": len(analyzed_sources)
        }
        
        return {
            "critical_issues": critical_issues,
            "warnings": warnings,
            "system_status": system_status,
            "log_sources_analyzed": analyzed_sources,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing all logs: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}
