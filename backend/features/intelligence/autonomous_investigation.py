"""
Autonomous Investigation Mode
Trigger a fully autonomous investigation from a single IOC or alert.
Agent independently pivots across: threat intel, infrastructure, sandbox, OSINT, logs.
Builds complete attack picture without requiring user prompts at each step.
Self-directs the investigation following a structured methodology.
Delivers complete investigation report when done.
Activate with: "investigate autonomously: [IOC/alert]"
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from urllib.parse import urlparse

from backend.tools import execute_tool, tool_schemas
from backend.model_router import ROUTER
from backend.configs import settings as config

log = logging.getLogger("autonomous_investigation")


class InvestigationPhase(Enum):
    IOC_ENRICHMENT = "ioc_enrichment"
    INFRASTRUCTURE_PIVOT = "infrastructure_pivot"
    MALWARE_SAMPLES = "malware_samples"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    MITRE_MAPPING = "mitre_mapping"
    THREAT_ACTOR_ATTRIBUTION = "threat_actor_attribution"
    PREDICTIVE_NEXT_ACTIONS = "predictive_next_actions"
    REPORT_GENERATION = "report_generation"


@dataclass
class InvestigationStep:
    phase: InvestigationPhase
    description: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = "pending"
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class InvestigationResult:
    investigation_id: str
    initial_ioc: str
    steps: List[InvestigationStep]
    final_report: Optional[Dict[str, Any]] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "running"


class AutonomousInvestigator:
    """
    Fully autonomous investigation engine.
    Takes a single IOC/alert and builds complete attack picture.
    """

    def __init__(self):
        self.active_investigations: Dict[str, InvestigationResult] = {}
        self.max_concurrent = 3

    async def investigate(
        self,
        ioc: str,
        context: Optional[Dict[str, Any]] = None,
        depth: str = "standard"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run autonomous investigation on an IOC.
        Yields progress updates and final report.
        """
        investigation_id = str(uuid.uuid4())[:12]
        result = InvestigationResult(
            investigation_id=investigation_id,
            initial_ioc=ioc,
            steps=[]
        )
        self.active_investigations[investigation_id] = result

        try:
            yield {
                "type": "investigation_started",
                "data": {
                    "investigation_id": investigation_id,
                    "initial_ioc": ioc,
                    "phases": [p.value for p in InvestigationPhase]
                }
            }

            # Phase 1: IOC Enrichment
            yield await self._phase_ioc_enrichment(result, ioc, context)

            # Phase 2: Infrastructure Pivot
            yield await self._phase_infrastructure_pivot(result)

            # Phase 3: Malware Samples
            yield await self._phase_malware_samples(result)

            # Phase 4: Behavioral Analysis
            yield await self._phase_behavioral_analysis(result)

            # Phase 5: MITRE ATT&CK Mapping
            yield await self._phase_mitre_mapping(result)

            # Phase 6: Threat Actor Attribution
            yield await self._phase_threat_actor_attribution(result)

            # Phase 7: Predictive Next Actions
            yield await self._phase_predictive_next_actions(result)

            # Phase 8: Report Generation
            final_report = await self._phase_report_generation(result)
            result.final_report = final_report
            result.completed_at = time.time()
            result.status = "completed"

            yield {
                "type": "investigation_completed",
                "data": {
                    "investigation_id": investigation_id,
                    "report": final_report,
                    "duration_seconds": result.completed_at - result.started_at
                }
            }

        except Exception as e:
            log.exception("Investigation failed")
            result.status = "failed"
            yield {
                "type": "investigation_error",
                "data": {
                    "investigation_id": investigation_id,
                    "error": str(e)
                }
            }

    async def _phase_ioc_enrichment(
        self,
        result: InvestigationResult,
        ioc: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.IOC_ENRICHMENT,
            description=f"Enrich IOC: {ioc}",
            input_data={"ioc": ioc, "context": context or {}}
        )
        step.started_at = time.time()
        result.steps.append(step)

        # Determine IOC type and enrich accordingly
        ioc_type = self._classify_ioc(ioc)
        enrichment_data = {}

        if ioc_type == "ip":
            enrichment_data = await self._enrich_ip(ioc)
        elif ioc_type == "domain":
            enrichment_data = await self._enrich_domain(ioc)
        elif ioc_type == "hash":
            enrichment_data = await self._enrich_hash(ioc)
        elif ioc_type == "url":
            enrichment_data = await self._enrich_url(ioc)
        elif ioc_type == "email":
            enrichment_data = await self._enrich_email(ioc)
        else:
            enrichment_data = await self._enrich_generic(ioc)

        step.output_data = enrichment_data
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.9

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": enrichment_data,
                "confidence": step.confidence
            }
        }

    async def _phase_infrastructure_pivot(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.INFRASTRUCTURE_PIVOT,
            description="Pivot to related infrastructure",
            input_data={"previous_output": result.steps[-1].output_data if result.steps else {}}
        )
        step.started_at = time.time()
        result.steps.append(step)

        ioc = result.initial_ioc
        ioc_type = self._classify_ioc(ioc)
        infrastructure = {}

        # Use CyberOps tools for infrastructure analysis
        try:
            # Passive DNS
            pdns_result = await execute_tool("cyberops", {"action": "passive_dns", "query": ioc})
            infrastructure["passive_dns"] = pdns_result

            # SSL certificate analysis
            if ioc_type in ["domain", "ip"]:
                ssl_result = await execute_tool("cyberops", {"action": "ssl_cert", "target": ioc})
                infrastructure["ssl_certificates"] = ssl_result

            # WHOIS
            whois_result = await execute_tool("cyberops", {"action": "whois", "query": ioc})
            infrastructure["whois"] = whois_result

            # Related infrastructure via graph analysis
            graph_result = await execute_tool("cyberops", {"action": "infrastructure_graph", "seed": ioc})
            infrastructure["graph"] = graph_result

        except Exception as e:
            log.warning(f"Infrastructure pivot partial: {e}")

        step.output_data = infrastructure
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.85

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": infrastructure,
                "confidence": step.confidence
            }
        }

    async def _phase_malware_samples(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.MALWARE_SAMPLES,
            description="Find associated malware samples",
            input_data={"infrastructure": result.steps[-1].output_data if result.steps else {}}
        )
        step.started_at = time.time()
        result.steps.append(step)

        samples = {}
        try:
            # Query malware repositories via hash/ioc
            ioc = result.initial_ioc
            if self._classify_ioc(ioc) == "hash":
                # Direct hash lookup
                vt_result = await execute_tool("cyberops", {"action": "virustotal", "hash": ioc})
                samples["virustotal"] = vt_result

                mb_result = await execute_tool("cyberops", {"action": "malwarebazaar", "hash": ioc})
                samples["malwarebazaar"] = mb_result
            else:
                # Search by IOC
                search_result = await execute_tool("cyberops", {"action": "malware_search", "ioc": ioc})
                samples["search"] = search_result

            # YARA rule matching if we have samples
            if samples:
                yara_result = await execute_tool("cyberops", {"action": "yara_scan", "samples": list(samples.keys())})
                samples["yara_matches"] = yara_result

        except Exception as e:
            log.warning(f"Malware sample collection partial: {e}")

        step.output_data = samples
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.8

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": samples,
                "confidence": step.confidence
            }
        }

    async def _phase_behavioral_analysis(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.BEHAVIORAL_ANALYSIS,
            description="Behavioral analysis in sandbox",
            input_data={"samples": result.steps[-1].output_data if result.steps else {}}
        )
        step.started_at = time.time()
        result.steps.append(step)

        behavior = {}
        try:
            # Sandbox analysis
            samples = result.steps[-1].output_data or {}
            for sample_id, sample_data in samples.items():
                if isinstance(sample_data, dict) and "hash" in sample_data:
                    sandbox_result = await execute_tool("cyberops", {
                        "action": "sandbox",
                        "hash": sample_data["hash"],
                        "timeout": 300
                    })
                    behavior[sample_id] = sandbox_result

            # Network behavior
            net_result = await execute_tool("cyberops", {"action": "network_behavior", "ioc": result.initial_ioc})
            behavior["network"] = net_result

            # Process behavior
            proc_result = await execute_tool("cyberops", {"action": "process_behavior", "ioc": result.initial_ioc})
            behavior["process"] = proc_result

        except Exception as e:
            log.warning(f"Behavioral analysis partial: {e}")

        step.output_data = behavior
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.75

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": behavior,
                "confidence": step.confidence
            }
        }

    async def _phase_mitre_mapping(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.MITRE_MAPPING,
            description="Map behavior to MITRE ATT&CK",
            input_data={"behavior": result.steps[-1].output_data if result.steps else {}}
        )
        step.started_at = time.time()
        result.steps.append(step)

        mitre = {}
        try:
            behavior = result.steps[-1].output_data or {}
            mitre_result = await execute_tool("cyberops", {
                "action": "mitre",
                "behavior": behavior
            })
            mitre = mitre_result
        except Exception as e:
            log.warning(f"MITRE mapping partial: {e}")

        step.output_data = mitre
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.9

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": mitre,
                "confidence": step.confidence
            }
        }

    async def _phase_threat_actor_attribution(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.THREAT_ACTOR_ATTRIBUTION,
            description="Attribute to threat actor",
            input_data={
                "mitre": result.steps[-1].output_data if result.steps else {},
                "infrastructure": result.steps[1].output_data if len(result.steps) > 1 else {}
            }
        )
        step.started_at = time.time()
        result.steps.append(step)

        attribution = {}
        try:
            # Use LLM for attribution analysis
            route, brain = ROUTER.resolve("auto")
            if brain:
                prompt = self._build_attribution_prompt(result)
                response = await brain.ainvoke(prompt)
                attribution["llm_analysis"] = response.content if hasattr(response, 'content') else str(response)

            # Compare against known actor profiles
            actor_profiles = await self._load_actor_profiles()
            attribution["profile_matches"] = self._match_actor_profiles(result, actor_profiles)

        except Exception as e:
            log.warning(f"Attribution partial: {e}")

        step.output_data = attribution
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.7

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": attribution,
                "confidence": step.confidence
            }
        }

    async def _phase_predictive_next_actions(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.PREDICTIVE_NEXT_ACTIONS,
            description="Predict next attacker actions",
            input_data={
                "attribution": result.steps[-1].output_data if result.steps else {},
                "mitre": result.steps[4].output_data if len(result.steps) > 4 else {},
                "current_state": self._assess_current_state(result)
            }
        )
        step.started_at = time.time()
        result.steps.append(step)

        predictions = {}
        try:
            route, brain = ROUTER.resolve("auto")
            if brain:
                prompt = self._build_prediction_prompt(result)
                response = await brain.ainvoke(prompt)
                predictions["llm_predictions"] = response.content if hasattr(response, 'content') else str(response)

            # Rule-based predictions from MITRE
            predictions["rule_based"] = self._rule_based_predictions(result)

        except Exception as e:
            log.warning(f"Prediction partial: {e}")

        step.output_data = predictions
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.75

        return {
            "type": "phase_completed",
            "data": {
                "phase": step.phase.value,
                "output": predictions,
                "confidence": step.confidence
            }
        }

    async def _phase_report_generation(self, result: InvestigationResult) -> Dict[str, Any]:
        step = InvestigationStep(
            phase=InvestigationPhase.REPORT_GENERATION,
            description="Generate unified investigation report",
            input_data={"all_phases": [s.output_data for s in result.steps]}
        )
        step.started_at = time.time()

        report = {
            "investigation_id": result.investigation_id,
            "initial_ioc": result.initial_ioc,
            "timestamp": datetime.fromtimestamp(result.started_at).isoformat(),
            "duration_seconds": time.time() - result.started_at,
            "executive_summary": "",
            "phases": {},
            "indicators": [],
            "mitre_techniques": [],
            "threat_actor": {},
            "predictions": [],
            "recommendations": []
        }

        # Aggregate all phase outputs
        for s in result.steps:
            report["phases"][s.phase.value] = s.output_data

        # Generate executive summary via LLM
        try:
            route, brain = ROUTER.resolve("auto")
            if brain:
                prompt = self._build_report_prompt(result)
                response = await brain.ainvoke(prompt)
                report["executive_summary"] = response.content if hasattr(response, 'content') else str(response)
        except Exception:
            report["executive_summary"] = "Automated investigation completed. See phase details."

        # Extract indicators
        report["indicators"] = self._extract_all_indicators(result)

        # Extract MITRE techniques
        if "mitre" in report["phases"]:
            report["mitre_techniques"] = self._extract_mitre_techniques(report["phases"]["mitre"])

        # Threat actor
        if "threat_actor" in report["phases"]:
            report["threat_actor"] = report["phases"]["threat_actor"]

        # Predictions
        if "predictive_next_actions" in report["phases"]:
            report["predictions"] = report["phases"]["predictive_next_actions"]

        # Recommendations
        report["recommendations"] = self._generate_recommendations(result)

        step.output_data = report
        step.completed_at = time.time()
        step.status = "completed"
        step.confidence = 0.95

        return report

    # Helper methods
    def _classify_ioc(self, ioc: str) -> str:
        """Classify IOC type."""
        ioc = ioc.strip()
        if all(c in '0123456789abcdefABCDEF' for c in ioc) and len(ioc) in [32, 40, 64]:
            return "hash"
        elif '.' in ioc and not ' ' in ioc and not ioc.startswith('http'):
            parts = ioc.split('.')
            if all(p.isdigit() and 0 <= int(p) <= 255 for p in parts) and len(parts) == 4:
                return "ip"
            return "domain"
        elif ioc.startswith(('http://', 'https://')):
            return "url"
        elif '@' in ioc and '.' in ioc.split('@')[-1]:
            return "email"
        return "unknown"

    async def _enrich_ip(self, ip: str) -> Dict[str, Any]:
        """Enrich IP address."""
        results = {}
        try:
            results["geoip"] = await execute_tool("cyberops", {"action": "geoip", "ip": ip})
            results["reputation"] = await execute_tool("cyberops", {"action": "ip_reputation", "ip": ip})
            results["shodan"] = await execute_tool("cyberops", {"action": "shodan", "ip": ip})
        except Exception:
            pass
        return results

    async def _enrich_domain(self, domain: str) -> Dict[str, Any]:
        """Enrich domain."""
        results = {}
        try:
            results["dns"] = await execute_tool("cyberops", {"action": "dns", "domain": domain})
            results["subdomains"] = await execute_tool("cyberops", {"action": "subdomains", "domain": domain})
            results["reputation"] = await execute_tool("cyberops", {"action": "domain_reputation", "domain": domain})
        except Exception:
            pass
        return results

    async def _enrich_hash(self, hash_val: str) -> Dict[str, Any]:
        """Enrich file hash."""
        results = {}
        try:
            results["vt"] = await execute_tool("cyberops", {"action": "virustotal", "hash": hash_val})
            results["mb"] = await execute_tool("cyberops", {"action": "malwarebazaar", "hash": hash_val})
            results["hybrid"] = await execute_tool("cyberops", {"action": "hybrid_analysis", "hash": hash_val})
        except Exception:
            pass
        return results

    async def _enrich_url(self, url: str) -> Dict[str, Any]:
        """Enrich URL."""
        results = {}
        try:
            parsed = urlparse(url)
            results["domain"] = await self._enrich_domain(parsed.netloc)
            results["urlscan"] = await execute_tool("cyberops", {"action": "urlscan", "url": url})
        except Exception:
            pass
        return results

    async def _enrich_email(self, email: str) -> Dict[str, Any]:
        """Enrich email address."""
        results = {}
        try:
            domain = email.split('@')[-1]
            results["domain"] = await self._enrich_domain(domain)
            results["breach"] = await execute_tool("cyberops", {"action": "haveibeenpwned", "email": email})
        except Exception:
            pass
        return results

    async def _enrich_generic(self, ioc: str) -> Dict[str, Any]:
        """Generic enrichment."""
        return {"raw": ioc, "note": "Unknown IOC type - manual analysis required"}

    def _build_attribution_prompt(self, result: InvestigationResult) -> str:
        phases = {s.phase.value: s.output_data for s in result.steps}
        return f"""Analyze this investigation data and attribute to threat actor(s):

Initial IOC: {result.initial_ioc}
Phases: {json.dumps(phases, default=str, indent=2)}

Provide:
1. Most likely threat actor(s) with confidence
2. Supporting evidence from each phase
3. TTP overlaps with known actor profiles
4. Alternative hypotheses
5. Confidence assessment"""

    def _build_prediction_prompt(self, result: InvestigationResult) -> str:
        phases = {s.phase.value: s.output_data for s in result.steps}
        return f"""Predict next attacker actions based on investigation:

Initial IOC: {result.initial_ioc}
Current state: {self._assess_current_state(result)}
MITRE techniques: {phases.get('mitre_mapping', {})}
Attribution: {phases.get('threat_actor_attribution', {})}

Provide:
1. Top 3 predicted next moves with probability scores
2. MITRE techniques likely to be used
3. Timeline estimates
4. Recommended defensive actions to pre-position
5. Detection opportunities for each prediction"""

    def _build_report_prompt(self, result: InvestigationResult) -> str:
        phases = {s.phase.value: s.output_data for s in result.steps}
        return f"""Generate executive summary for this investigation report:

Investigation ID: {result.investigation_id}
Initial IOC: {result.initial_ioc}
Duration: {time.time() - result.started_at:.0f}s

Phase outputs: {json.dumps(phases, default=str, indent=2)}

Write a concise executive summary (3-5 paragraphs) covering:
1. What was investigated
2. Key findings
3. Threat actor assessment
4. Predicted next actions
5. Immediate recommendations"""

    async def _load_actor_profiles(self) -> Dict[str, Any]:
        """Load known threat actor profiles."""
        # In production, load from threat intel database
        return {
            "APT28": {"techniques": ["T1566", "T1059", "T1021"], "targets": ["government", "military"], "region": "global"},
            "APT29": {"techniques": ["T1566", "T1555", "T1003"], "targets": ["government", "think_tanks"], "region": "global"},
            "Lazarus": {"techniques": ["T1566", "T1204", "T1486"], "targets": ["financial", "crypto"], "region": "global"},
            "FIN7": {"techniques": ["T1566", "T1059", "T1005"], "targets": ["retail", "hospitality"], "region": "global"},
        }

    def _match_actor_profiles(self, result: InvestigationResult, profiles: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Match investigation data against actor profiles."""
        matches = []
        mitre_techniques = set()
        if len(result.steps) > 4 and result.steps[4].output_data:
            mitre_data = result.steps[4].output_data
            if isinstance(mitre_data, dict) and "techniques" in mitre_data:
                mitre_techniques = set(mitre_data["techniques"])

        for actor, profile in profiles.items():
            actor_techniques = set(profile.get("techniques", []))
            overlap = mitre_techniques & actor_techniques
            if overlap:
                matches.append({
                    "actor": actor,
                    "matching_techniques": list(overlap),
                    "confidence": len(overlap) / max(len(actor_techniques), 1),
                    "profile": profile
                })

        return sorted(matches, key=lambda x: x["confidence"], reverse=True)

    def _assess_current_state(self, result: InvestigationResult) -> str:
        """Assess current attacker state."""
        return "Initial access achieved, lateral movement likely in progress"

    def _rule_based_predictions(self, result: InvestigationResult) -> List[Dict[str, Any]]:
        """Generate rule-based predictions."""
        predictions = []
        mitre_data = result.steps[4].output_data if len(result.steps) > 4 else {}
        techniques = mitre_data.get("techniques", []) if isinstance(mitre_data, dict) else []

        # Common progression patterns
        if "T1078" in techniques:  # Valid Accounts
            predictions.append({
                "action": "Credential Access - OS Credential Dumping",
                "technique": "T1003",
                "probability": 0.85,
                "eta_hours": 2
            })
        if "T1021" in techniques:  # Remote Services
            predictions.append({
                "action": "Lateral Movement - SMB/Windows Admin Shares",
                "technique": "T1021.002",
                "probability": 0.75,
                "eta_hours": 4
            })

        return predictions

    def _extract_all_indicators(self, result: InvestigationResult) -> List[Dict[str, Any]]:
        """Extract all IOCs from investigation."""
        indicators = []
        for step in result.steps:
            if step.output_data:
                self._extract_iocs_from_dict(step.output_data, indicators, step.phase.value)
        return indicators

    def _extract_iocs_from_dict(self, data: Any, indicators: List, source: str):
        """Recursively extract IOCs from data."""
        if isinstance(data, dict):
            for k, v in data.items():
                if k in ["ip", "domain", "hash", "url", "email", "md5", "sha1", "sha256", "sha512"]:
                    indicators.append({"type": k, "value": v, "source": source})
                elif isinstance(v, (dict, list)):
                    self._extract_iocs_from_dict(v, indicators, source)
        elif isinstance(data, list):
            for item in data:
                self._extract_iocs_from_dict(item, indicators, source)

    def _extract_mitre_techniques(self, mitre_data: Any) -> List[Dict[str, Any]]:
        """Extract MITRE techniques."""
        techniques = []
        if isinstance(mitre_data, dict):
            for k, v in mitre_data.items():
                if "technique" in k.lower() or "tactic" in k.lower():
                    techniques.append({k: v})
        return techniques

    def _generate_recommendations(self, result: InvestigationResult) -> List[str]:
        """Generate actionable recommendations."""
        recs = [
            "Block identified IOCs at network perimeter",
            "Enable enhanced logging for predicted MITRE techniques",
            "Hunt for lateral movement indicators in environment",
            "Review and update detection rules for identified TTPs",
            "Conduct targeted threat hunt based on predictions"
        ]
        return recs


# Global instance
INVESTIGATOR = AutonomousInvestigator()


async def investigate_autonomously(
    ioc: str,
    context: Optional[Dict[str, Any]] = None,
    depth: str = "standard"
) -> AsyncGenerator[Dict[str, Any], None]:
    """Entry point for autonomous investigation."""
    async for update in INVESTIGATOR.investigate(ioc, context, depth):
        yield update