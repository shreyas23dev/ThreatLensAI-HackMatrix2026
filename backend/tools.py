from typing import Dict, Any, List
import json
import os
import random

TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_vulnerabilities",
            "description": "Fetch all vulnerabilities currently tracked in the system, optionally filtering by severity or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status: UNASSIGNED, IN_TRIAGE, REMEDIATION_PENDING, SUPPRESSED, RESOLVED"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_random_nvd_cves",
            "description": "Select N random CVEs (default 20) from the full NVD dataset, parse their metrics, calculate PSSS priority scores, and load them into the system for prioritization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of random CVEs to load from NVD dataset (default 20)"
                    },
                    "load_into_triage": {
                        "type": "boolean",
                        "description": "Whether to load these CVEs into active system memory for triage (default True)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_vulnerability_status",
            "description": "Update the lifecycle status of a specific vulnerability by its CVE ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "v_id": {
                        "type": "string",
                        "description": "Vulnerability ID, e.g., 'CVE-2024-3094'"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status: UNASSIGNED, IN_TRIAGE, REMEDIATION_PENDING, SUPPRESSED, RESOLVED"
                    }
                },
                "required": ["v_id", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_vulnerability_priority",
            "description": "Assign or update the severity rating/priority level (CRITICAL, HIGH, MEDIUM, LOW) or custom PSSS priority score for a specific vulnerability by its CVE ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "v_id": {
                        "type": "string",
                        "description": "Vulnerability ID, e.g., 'CVE-2024-3094'"
                    },
                    "severity": {
                        "type": "string",
                        "description": "New priority severity rating: CRITICAL, HIGH, MEDIUM, LOW"
                    },
                    "psssScore": {
                        "type": "number",
                        "description": "Custom PSSS priority score override (0.0 to 10.0)"
                    }
                },
                "required": ["v_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_threat_actors",
            "description": "Fetch list of known threat actors, their target sectors, MITRE techniques, and indicators of compromise (IOCs).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_audit_logs",
            "description": "Retrieve recent system audit log events including user actions, weight overrides, and data sync events.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_health",
            "description": "Fetch current status, sync frequency, and record count for backend data pipelines (NVD, EPSS, MITRE ATT&CK).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_scoring_weights",
            "description": "Fetch current PSSS scoring formula weights (CVSS weight, EPSS weight, Asset Criticality weight, Threat Actor multiplier).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_scoring_weights",
            "description": "Recalibrate the PSSS scoring weights used to compute vulnerability risk scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cvssWeight": { "type": "number", "description": "Weight for CVSS score (0.0 to 1.0)" },
                    "epssWeight": { "type": "number", "description": "Weight for EPSS score (0.0 to 1.0)" },
                    "assetCriticalityWeight": { "type": "number", "description": "Weight for asset criticality (0.0 to 1.0)" },
                    "threatActorMultiplier": { "type": "number", "description": "Multiplier for threat actor presence" }
                },
                "required": ["cvssWeight", "epssWeight", "assetCriticalityWeight", "threatActorMultiplier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "predict_cve_vector",
            "description": "Use machine learning to predict CVSS 3.1 metrics and PSSS priority score from a raw CVE description text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The raw vulnerability description text to analyze"
                    }
                },
                "required": ["text"]
            }
        }
    }
]

def get_tools_schema() -> List[Dict[str, Any]]:
    return TOOLS_SCHEMA

def execute_tool(tool_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the specified tool using backend context (stores and helper functions).
    """
    vulnerabilities_store = context["vulnerabilities_store"]
    threat_actors_store = context["threat_actors_store"]
    audit_logs_store = context["audit_logs_store"]
    weights_store = context["weights_store"]
    pipeline_health_func = context["get_pipeline_health_func"]
    update_v_status_func = context["update_v_status_func"]
    update_v_priority_func = context.get("update_v_priority_func")
    update_weights_func = context["update_weights_func"]
    predict_cve_func = context["predict_cve_func"]

    if tool_name == "get_vulnerabilities":
        severity_filter = args.get("severity")
        status_filter = args.get("status")
        result = vulnerabilities_store
        if severity_filter:
            result = [v for v in result if str(v.get("severity", "")).upper() == str(severity_filter).upper()]
        if status_filter:
            result = [v for v in result if str(v.get("status", "")).upper() == str(status_filter).upper()]
        return {"success": True, "vulnerabilities": result, "count": len(result)}

    elif tool_name == "get_random_nvd_cves":
        count = int(args.get("count", 20))
        load_into_triage = bool(args.get("load_into_triage", True))
        nvd_path = "nvdcve-2.0-modified.json"
        
        if not os.path.exists(nvd_path):
            return {"error": f"NVD dataset '{nvd_path}' not found on backend server."}

        try:
            with open(nvd_path, "r", encoding="utf-8") as f:
                nvd_data = json.load(f)
            
            raw_items = nvd_data.get("vulnerabilities", [])
            if not raw_items:
                return {"error": "NVD dataset contains no vulnerability entries."}

            sampled_raw = random.sample(raw_items, min(count, len(raw_items)))
            sampled_cves = []

            for idx, item in enumerate(sampled_raw):
                cve = item.get("cve", {})
                cve_id = cve.get("id", f"CVE-2024-{random.randint(1000, 9999)}")
                descs = cve.get("descriptions", [])
                desc_text = descs[0].get("value", "No description provided.") if descs else "No description provided."

                cvss_score = 7.5
                vector_str = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                metrics_data = cve.get("metrics", {})
                if "cvssMetricV31" in metrics_data and metrics_data["cvssMetricV31"]:
                    m = metrics_data["cvssMetricV31"][0]
                    cvss_data = m.get("cvssData", {})
                    cvss_score = float(cvss_data.get("baseScore", 7.5))
                    vector_str = cvss_data.get("vectorString", vector_str)

                # Heuristic EPSS exploit score estimation
                epss_score = round(min(0.99, max(0.01, (cvss_score / 10.0) * random.uniform(0.7, 1.05))), 3)

                # Tactics inference
                desc_lower = desc_text.lower()
                tactics = []
                if any(w in desc_lower for w in ["remote code execution", "rce", "unauthenticated", "buffer overflow", "xss"]):
                    tactics.append("Initial Access")
                if any(w in desc_lower for w in ["privilege escalation", "use after free", "kernel", "root", "elevation"]):
                    tactics.append("Privilege Escalation")
                if any(w in desc_lower for w in ["bypass", "sandbox", "escape"]):
                    tactics.append("Defense Evasion")
                if any(w in desc_lower for w in ["execution", "arbitrary code"]):
                    tactics.append("Execution")
                if not tactics:
                    tactics = ["Initial Access"]

                # PSSS calculation
                alpha = weights_store.get("cvssWeight", 0.35)
                beta = weights_store.get("epssWeight", 0.45)
                gamma = weights_store.get("assetCriticalityWeight", 0.20)
                attack_crit = 1.0 if any(t in ["Initial Access", "Privilege Escalation", "Execution"] for t in tactics) else 0.5
                psss = round(float(min(10.0, (alpha * (cvss_score / 10.0) + beta * epss_score + gamma * attack_crit) * 10.0)), 2)

                severity = "CRITICAL" if psss >= 9.0 else ("HIGH" if psss >= 7.0 else ("MEDIUM" if psss >= 4.0 else "LOW"))

                cve_obj = {
                    "id": cve_id,
                    "title": f"NVD {cve_id} Vulnerability",
                    "psssScore": psss,
                    "cvssScore": cvss_score,
                    "epssScore": epss_score,
                    "severity": severity,
                    "vector": vector_str,
                    "component": f"component-node-{idx + 1}",
                    "affectedNodes": random.randint(12, 450),
                    "status": "UNASSIGNED",
                    "cwe": "CWE-Generic",
                    "mitreTactics": tactics,
                    "discoveredAt": "2024-03-30T12:00:00Z",
                    "activeExploits": epss_score > 0.6,
                    "description": desc_text,
                    "remediationAction": f"Update package associated with {cve_id} to latest security release."
                }
                sampled_cves.append(cve_obj)

            if load_into_triage:
                # Add loaded CVEs to system store (avoiding duplicate IDs)
                existing_ids = {v["id"] for v in vulnerabilities_store}
                new_added = [v for v in sampled_cves if v["id"] not in existing_ids]
                vulnerabilities_store.extend(new_added)
                # Sort descending by PSSS score
                vulnerabilities_store.sort(key=lambda x: x["psssScore"], reverse=True)

            return {
                "success": True,
                "count": len(sampled_cves),
                "loaded_into_triage": load_into_triage,
                "cves": sampled_cves
            }
        except Exception as e:
            return {"error": f"Failed to parse random CVEs from NVD dataset: {str(e)}"}

    elif tool_name == "update_vulnerability_status":
        v_id = args.get("v_id")
        status = args.get("status")
        if not v_id or not status:
            return {"error": "Missing required arguments v_id and status"}
        try:
            updated = update_v_status_func(v_id, status)
            return {"success": True, "updatedVulnerability": updated}
        except Exception as e:
            return {"error": str(e)}

    elif tool_name == "update_vulnerability_priority":
        v_id = args.get("v_id")
        severity = args.get("severity")
        psssScore = args.get("psssScore")
        if not v_id:
            return {"error": "Missing required argument v_id"}
        if severity is None and psssScore is None:
            return {"error": "Must provide at least one of 'severity' or 'psssScore' to update priority."}
        try:
            if update_v_priority_func:
                updated = update_v_priority_func(v_id, severity, psssScore)
                return {"success": True, "updatedVulnerability": updated}
            return {"error": "Priority update function not configured in backend context."}
        except Exception as e:
            return {"error": str(e)}

    elif tool_name == "get_threat_actors":
        return {"success": True, "threatActors": threat_actors_store, "count": len(threat_actors_store)}

    elif tool_name == "get_audit_logs":
        return {"success": True, "auditLogs": audit_logs_store, "count": len(audit_logs_store)}

    elif tool_name == "get_pipeline_health":
        health_data = pipeline_health_func()
        return {"success": True, "pipelineHealth": health_data}

    elif tool_name == "get_scoring_weights":
        return {"success": True, "weights": weights_store}

    elif tool_name == "update_scoring_weights":
        cvss_w = args.get("cvssWeight")
        epss_w = args.get("epssWeight")
        asset_w = args.get("assetCriticalityWeight")
        threat_m = args.get("threatActorMultiplier")
        if any(x is None for x in [cvss_w, epss_w, asset_w, threat_m]):
            return {"error": "All weight parameters (cvssWeight, epssWeight, assetCriticalityWeight, threatActorMultiplier) are required"}
        try:
            updated_w = update_weights_func(cvss_w, epss_w, asset_w, threat_m)
            return {"success": True, "weights": updated_w}
        except Exception as e:
            return {"error": str(e)}

    elif tool_name == "predict_cve_vector":
        text = args.get("text")
        if not text:
            return {"error": "Missing text argument for prediction"}
        try:
            res = predict_cve_func(text)
            return {"success": True, "prediction": res}
        except Exception as e:
            return {"error": str(e)}

    else:
        return {"error": f"Tool '{tool_name}' is not recognized."}
