"""
Real-Time Threat Correlation Engine
Correlate events across all data sources as they arrive:
- Ingest: SIEM alerts, EDR events, NDR detections, threat feeds simultaneously
- Identify: event chains that individually look benign but collectively indicate attack
- Alert threshold: raise severity automatically as correlation confidence grows
- Timeline: build real-time attack timeline as events are correlated
- Output: live threat picture updated with each new event
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set
from threading import Lock

log = logging.getLogger("threat_correlation")


class EventSource(Enum):
    SIEM = "siem"
    EDR = "edr"
    NDR = "ndr"
    THREAT_FEED = "threat_feed"
    FIREWALL = "firewall"
    PROXY = "proxy"
    DNS = "dns"
    AUTH = "auth"
    CLOUD = "cloud"
    CUSTOM = "custom"


class CorrelationType(Enum):
    TEMPORAL = "temporal"           # Events close in time
    ENTITY = "entity"               # Same host/user/account
    ATTACK_CHAIN = "attack_chain"   # MITRE technique sequence
    BEHAVIORAL = "behavioral"       # Similar behavior patterns
    INFRASTRUCTURE = "infrastructure"  # Shared infrastructure
    CAMPAIGN = "campaign"           # Known campaign indicators


@dataclass
class SecurityEvent:
    event_id: str
    source: EventSource
    timestamp: datetime
    raw_data: Dict[str, Any]
    normalized: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, List[str]] = field(default_factory=dict)  # entity_type -> values
    mitre_techniques: List[str] = field(default_factory=list)
    severity: str = "info"
    tags: List[str] = field(default_factory=list)


@dataclass
class CorrelationRule:
    rule_id: str
    name: str
    description: str
    correlation_type: CorrelationType
    conditions: Dict[str, Any]
    min_events: int = 2
    time_window_seconds: int = 3600
    severity_boost: int = 1
    enabled: bool = True
    mitre_techniques: List[str] = field(default_factory=list)


@dataclass
class CorrelationMatch:
    match_id: str
    rule: CorrelationRule
    events: List[SecurityEvent]
    matched_at: datetime
    confidence: float
    correlated_entities: Dict[str, List[str]] = field(default_factory=dict)
    attack_timeline: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = "medium"


class ThreatCorrelationEngine:
    """
    Real-time threat correlation engine.
    Ingests events from multiple sources and identifies correlated attack chains.
    """

    def __init__(self, max_events: int = 100000, window_hours: int = 24):
        self.max_events = max_events
        self.window_hours = window_hours
        self.events: deque = deque(maxlen=max_events)
        self.events_by_entity: Dict[str, Dict[str, List[SecurityEvent]]] = defaultdict(lambda: defaultdict(list))
        self.events_by_time: Dict[str, List[SecurityEvent]] = defaultdict(list)
        self.rules: Dict[str, CorrelationRule] = {}
        self.active_matches: Dict[str, CorrelationMatch] = {}
        self.match_history: List[CorrelationMatch] = []
        self._lock = Lock()
        self._event_counter = 0
        self._callbacks: List[Callable[[CorrelationMatch], Any]] = []

        # Initialize default rules
        self._init_default_rules()

    def _init_default_rules(self):
        """Initialize built-in correlation rules."""
        default_rules = [
            CorrelationRule(
                rule_id="brute_force_ssh",
                name="SSH Brute Force",
                description="Multiple failed SSH logins followed by success",
                correlation_type=CorrelationType.ATTACK_CHAIN,
                conditions={
                    "sequence": [
                        {"event_type": "auth_failure", "min_count": 5},
                        {"event_type": "auth_success", "within_seconds": 300}
                    ]
                },
                min_events=6,
                time_window_seconds=600,
                severity_boost=2,
                mitre_techniques=["T1110.001", "T1021.004"]
            ),
            CorrelationRule(
                rule_id="lateral_movement_smb",
                name="SMB Lateral Movement",
                description="SMB session creation followed by remote execution",
                correlation_type=CorrelationType.ATTACK_CHAIN,
                conditions={
                    "sequence": [
                        {"event_type": "smb_session", "min_count": 1},
                        {"event_type": "process_create", "command_contains": ["psexec", "wmiexec", "smbexec"], "within_seconds": 600}
                    ]
                },
                min_events=2,
                time_window_seconds=900,
                severity_boost=2,
                mitre_techniques=["T1021.002", "T1047"]
            ),
            CorrelationRule(
                rule_id="credential_dumping",
                name="Credential Dumping",
                description="LSASS access followed by suspicious outbound",
                correlation_type=CorrelationType.ATTACK_CHAIN,
                conditions={
                    "sequence": [
                        {"event_type": "process_access", "target": "lsass.exe"},
                        {"event_type": "network_connection", "suspicious": True, "within_seconds": 1800}
                    ]
                },
                min_events=2,
                time_window_seconds=1800,
                severity_boost=3,
                mitre_techniques=["T1003.001", "T1041"]
            ),
            CorrelationRule(
                rule_id="persistence_scheduled_task",
                name="Scheduled Task Persistence",
                description="Scheduled task creation with suspicious command",
                correlation_type=CorrelationType.BEHAVIORAL,
                conditions={
                    "event_type": "scheduled_task_create",
                    "command_suspicious": True
                },
                min_events=1,
                time_window_seconds=3600,
                severity_boost=2,
                mitre_techniques=["T1053.005"]
            ),
            CorrelationRule(
                rule_id="data_staging",
                name="Data Staging",
                description="Large file creation in temp followed by archive",
                correlation_type=CorrelationType.BEHAVIORAL,
                conditions={
                    "sequence": [
                        {"event_type": "file_create", "size_mb": {"gt": 100}, "path_contains": ["temp", "tmp", "users\\public"]},
                        {"event_type": "process_create", "command_contains": ["rar", "7z", "zip", "tar"], "within_seconds": 3600}
                    ]
                },
                min_events=2,
                time_window_seconds=7200,
                severity_boost=2,
                mitre_techniques=["T1074.001", "T1560"]
            ),
            CorrelationRule(
                rule_id="c2_beaconing",
                name="C2 Beaconing",
                description="Regular network connections to same destination",
                correlation_type=CorrelationType.TEMPORAL,
                conditions={
                    "event_type": "network_connection",
                    "beaconing": True,
                    "interval_variance_pct": {"lt": 20},
                    "min_connections": 10
                },
                min_events=10,
                time_window_seconds=3600,
                severity_boost=3,
                mitre_techniques=["T1071.001", "T1573"]
            ),
            CorrelationRule(
                rule_id="multi_source_same_entity",
                name="Multi-Source Entity Correlation",
                description="Same entity seen in multiple sources within time window",
                correlation_type=CorrelationType.ENTITY,
                conditions={
                    "min_sources": 3,
                    "entity_types": ["ip", "hostname", "user", "file_hash"]
                },
                min_events=3,
                time_window_seconds=1800,
                severity_boost=1
            ),
            CorrelationRule(
                rule_id="threat_feed_match",
                name="Threat Feed IOC Match",
                description="Internal event matches threat feed IOC",
                correlation_type=CorrelationType.INFRASTRUCTURE,
                conditions={
                    "source": EventSource.THREAT_FEED,
                    "match_field": ["ip", "domain", "hash", "url"]
                },
                min_events=2,
                time_window_seconds=86400,
                severity_boost=3
            )
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: CorrelationRule):
        """Add a correlation rule."""
        self.rules[rule.rule_id] = rule
        log.info(f"Added correlation rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """Remove a correlation rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]

    def register_callback(self, callback: Callable[[CorrelationMatch], Any]):
        """Register callback for new correlations."""
        self._callbacks.append(callback)

    def ingest_event(self, event: SecurityEvent) -> List[CorrelationMatch]:
        """Ingest a security event and check for correlations."""
        with self._lock:
            self._event_counter += 1
            if not event.event_id:
                event.event_id = f"evt_{self._event_counter}_{int(time.time())}"

            # Normalize event
            event.normalized = self._normalize_event(event)
            event.entities = self._extract_entities(event)
            event.mitre_techniques = self._extract_mitre(event)

            # Store event
            self.events.append(event)

            # Index by entity
            for entity_type, values in event.entities.items():
                for value in values:
                    self.events_by_entity[entity_type][value].append(event)

            # Index by time bucket (hour)
            time_bucket = event.timestamp.strftime("%Y%m%d%H")
            self.events_by_time[time_bucket].append(event)

            # Check correlations
            matches = self._check_correlations(event)

            # Trigger callbacks
            for match in matches:
                for callback in self._callbacks:
                    try:
                        callback(match)
                    except Exception as e:
                        log.warning(f"Correlation callback failed: {e}")

            return matches

    def _normalize_event(self, event: SecurityEvent) -> Dict[str, Any]:
        """Normalize event to common schema."""
        normalized = {
            "timestamp": event.timestamp.isoformat(),
            "source": event.source.value,
            "raw": event.raw_data
        }

        # Extract common fields based on source
        raw = event.raw_data
        if event.source == EventSource.SIEM:
            normalized.update({
                "event_type": raw.get("event_type") or raw.get("EventType") or "unknown",
                "host": raw.get("host") or raw.get("Computer") or raw.get("hostname"),
                "user": raw.get("user") or raw.get("User") or raw.get("TargetUserName"),
                "process": raw.get("process") or raw.get("Image") or raw.get("NewProcessName"),
                "command": raw.get("command") or raw.get("CommandLine"),
                "network": raw.get("network") or raw.get("DestinationIp") or raw.get("DestinationHostname")
            })
        elif event.source == EventSource.EDR:
            normalized.update({
                "event_type": raw.get("event_type") or raw.get("action_type") or "unknown",
                "host": raw.get("device") or raw.get("hostname") or raw.get("agent_hostname"),
                "user": raw.get("user") or raw.get("username"),
                "process": raw.get("process_name") or raw.get("file_path"),
                "command": raw.get("command_line") or raw.get("arguments"),
                "file_hash": raw.get("sha256") or raw.get("md5") or raw.get("file_hash")
            })
        elif event.source == EventSource.NDR:
            normalized.update({
                "event_type": raw.get("event_type") or raw.get("detection_type") or "unknown",
                "src_ip": raw.get("src_ip") or raw.get("source_ip"),
                "dst_ip": raw.get("dst_ip") or raw.get("destination_ip"),
                "src_port": raw.get("src_port"),
                "dst_port": raw.get("dst_port"),
                "protocol": raw.get("protocol"),
                "bytes": raw.get("bytes") or raw.get("total_bytes")
            })

        return normalized

    def _extract_entities(self, event: SecurityEvent) -> Dict[str, List[str]]:
        """Extract entities from event."""
        entities = defaultdict(list)
        norm = event.normalized

        # IP addresses
        for field in ["host", "src_ip", "dst_ip", "network"]:
            val = norm.get(field)
            if val and self._is_ip(val):
                entities["ip"].append(val)

        # Hostnames
        for field in ["host", "dst_ip", "network"]:
            val = norm.get(field)
            if val and not self._is_ip(val) and "." in val:
                entities["hostname"].append(val)

        # Users
        val = norm.get("user")
        if val:
            entities["user"].append(val)

        # File hashes
        val = norm.get("file_hash")
        if val:
            entities["file_hash"].append(val)

        # Processes
        val = norm.get("process")
        if val:
            entities["process"].append(val)

        return dict(entities)

    def _extract_mitre(self, event: SecurityEvent) -> List[str]:
        """Extract MITRE techniques from event."""
        techniques = []
        raw = event.raw_data

        # Direct MITRE tags
        if "mitre" in raw:
            if isinstance(raw["mitre"], list):
                techniques.extend(raw["mitre"])
            elif isinstance(raw["mitre"], str):
                techniques.append(raw["mitre"])

        # From tags
        for tag in event.tags:
            if tag.startswith("T") and tag[1:].isdigit():
                techniques.append(tag)

        return list(set(techniques))

    def _is_ip(self, value: str) -> bool:
        """Check if value is an IP address."""
        parts = value.split('.')
        return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

    def _check_correlations(self, new_event: SecurityEvent) -> List[CorrelationMatch]:
        """Check all rules against new event."""
        matches = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            rule_matches = self._evaluate_rule(rule, new_event)
            matches.extend(rule_matches)

        return matches

    def _evaluate_rule(self, rule: CorrelationRule, new_event: SecurityEvent) -> List[CorrelationMatch]:
        """Evaluate a single rule against recent events."""
        matches = []

        # Get candidate events within time window
        cutoff = new_event.timestamp - timedelta(seconds=rule.time_window_seconds)
        candidates = [e for e in self.events if e.timestamp >= cutoff and e.event_id != new_event.event_id]

        if rule.correlation_type == CorrelationType.ATTACK_CHAIN:
            matches = self._check_attack_chain(rule, new_event, candidates)
        elif rule.correlation_type == CorrelationType.ENTITY:
            matches = self._check_entity_correlation(rule, new_event, candidates)
        elif rule.correlation_type == CorrelationType.TEMPORAL:
            matches = self._check_temporal_correlation(rule, new_event, candidates)
        elif rule.correlation_type == CorrelationType.BEHAVIORAL:
            matches = self._check_behavioral_correlation(rule, new_event, candidates)
        elif rule.correlation_type == CorrelationType.INFRASTRUCTURE:
            matches = self._check_infrastructure_correlation(rule, new_event, candidates)
        elif rule.correlation_type == CorrelationType.CAMPAIGN:
            matches = self._check_campaign_correlation(rule, new_event, candidates)

        return matches

    def _check_attack_chain(self, rule: CorrelationRule, new_event: SecurityEvent, candidates: List[SecurityEvent]) -> List[CorrelationMatch]:
        """Check for attack chain sequence."""
        matches = []
        sequence = rule.conditions.get("sequence", [])

        if not sequence:
            return matches

        # Build timeline of relevant events
        relevant_events = [new_event] + candidates
        relevant_events.sort(key=lambda e: e.timestamp)

        # Check if sequence matches
        seq_idx = 0
        matched_events = []

        for event in relevant_events:
            if seq_idx >= len(sequence):
                break

            condition = sequence[seq_idx]
            if self._event_matches_condition(event, condition):
                matched_events.append(event)
                seq_idx += 1

        if seq_idx == len(sequence) and len(matched_events) >= rule.min_events:
            match = self._create_match(rule, matched_events, "attack_chain")
            matches.append(match)

        return matches

    def _check_entity_correlation(self, rule: CorrelationRule, new_event: SecurityEvent, candidates: List[SecurityEvent]) -> List[CorrelationMatch]:
        """Check for same entity across multiple sources."""
        matches = []

        entity_types = rule.conditions.get("entity_types", ["ip", "hostname", "user", "file_hash"])
        min_sources = rule.conditions.get("min_sources", 3)

        for entity_type in entity_types:
            new_values = new_event.entities.get(entity_type, [])
            if not new_values:
                continue

            for value in new_values:
                # Get all events with this entity
                entity_events = self.events_by_entity[entity_type].get(value, [])
                recent_events = [e for e in entity_events if e.timestamp >= new_event.timestamp - timedelta(seconds=rule.time_window_seconds)]

                sources = set(e.source for e in recent_events)
                if len(sources) >= min_sources:
                    match = self._create_match(rule, recent_events, f"entity_{entity_type}", correlated_entities={entity_type: [value]})
                    matches.append(match)

        return matches

    def _check_temporal_correlation(self, rule: CorrelationRule, new_event: SecurityEvent, candidates: List[SecurityEvent]) -> List[CorrelationMatch]:
        """Check for temporal patterns (beaconing, bursts)."""
        matches = []

        conditions = rule.conditions
        if conditions.get("event_type") and new_event.normalized.get("event_type") != conditions["event_type"]:
            return matches

        if conditions.get("beaconing"):
            # Check for regular intervals
            similar_events = [e for e in candidates if e.normalized.get("event_type") == new_event.normalized.get("event_type")]
            if len(similar_events) >= conditions.get("min_connections", 10):
                intervals = []
                for i in range(1, len(similar_events)):
                    interval = (similar_events[i].timestamp - similar_events[i-1].timestamp).total_seconds()
                    intervals.append(interval)

                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                    variance_pct = (variance ** 0.5 / avg_interval) * 100 if avg_interval > 0 else 100

                    if variance_pct < conditions.get("interval_variance_pct", 20):
                        match = self._create_match(rule, similar_events + [new_event], "beaconing")
                        matches.append(match)

        return matches

    def _check_behavioral_correlation(self, rule: CorrelationRule, new_event: SecurityEvent, candidates: List[SecurityEvent]) -> List[CorrelationMatch]:
        """Check for behavioral patterns."""
        matches = []

        conditions = rule.conditions
        if conditions.get("event_type") and new_event.normalized.get("event_type") != conditions["event_type"]:
            return matches

        # Sequence check
        sequence = conditions.get("sequence")
        if sequence:
            # Similar to attack chain but for behavioral patterns
            relevant_events = [new_event] + candidates
            relevant_events.sort(key=lambda e: e.timestamp)

            seq_idx = 0
            matched_events = []
            for event in relevant_events:
                if seq_idx >= len(sequence):
                    break
                if self._event_matches_condition(event, sequence[seq_idx]):
                    matched_events.append(event)
                    seq_idx += 1

            if seq_idx == len(sequence) and len(matched_events) >= rule.min_events:
                match = self._create_match(rule, matched_events, "behavioral")
                matches.append(match)

        # Single event suspicious command check
        elif conditions.get("command_suspicious"):
            cmd = new_event.normalized.get("command", "").lower()
            suspicious_patterns = ["powershell -enc", "cmd /c", "wscript", "cscript", "rundll32", "regsvr32", "mshta", "certutil", "bitsadmin"]
            if any(p in cmd for p in suspicious_patterns):
                match = self._create_match(rule, [new_event], "suspicious_command")
                matches.append(match)

        return matches

    def _check_infrastructure_correlation(self, rule: CorrelationRule, new_event: SecurityEvent, candidates: List[SecurityEvent]) -> List[CorrelationMatch]:
        """Check for threat feed matches."""
        matches = []

        conditions = rule.conditions
        match_fields = conditions.get("match_field", ["ip", "domain", "hash", "url"])

        # Check if new event matches any threat feed IOC
        for field in match_fields:
            new_values = new_event.entities.get(field, [])
            if not new_values:
                continue

            # Check against threat feed events
            feed_events = [e for e in candidates if e.source == EventSource.THREAT_FEED]
            for feed_event in feed_events:
                feed_values = feed_event.entities.get(field, [])
                intersection = set(new_values) & set(feed_values)
                if intersection:
                    match = self._create_match(
                        rule,
                        [new_event, feed_event],
                        f"threat_feed_{field}",
                        correlated_entities={field: list(intersection)}
                    )
                    matches.append(match)

        return matches

    def _check_campaign_correlation(self, rule: CorrelationRule, new_event: SecurityEvent, candidates: List[SecurityEvent]) -> List[CorrelationMatch]:
        """Check for known campaign indicators."""
        # Placeholder for campaign correlation
        return []

    def _event_matches_condition(self, event: SecurityEvent, condition: Dict[str, Any]) -> bool:
        """Check if event matches a condition."""
        # Event type
        if "event_type" in condition:
            if event.normalized.get("event_type") != condition["event_type"]:
                return False

        # Target process
        if "target" in condition:
            proc = event.normalized.get("process", "").lower()
            if condition["target"].lower() not in proc:
                return False

        # Command contains
        if "command_contains" in condition:
            cmd = event.normalized.get("command", "").lower()
            if not any(p.lower() in cmd for p in condition["command_contains"]):
                return False

        # Path contains
        if "path_contains" in condition:
            # Would need file path in normalized
            pass

        # File size
        if "size_mb" in condition:
            # Would need file size in normalized
            pass

        # Suspicious network
        if condition.get("suspicious"):
            # Check for suspicious ports, protocols, etc.
            pass

        return True

    def _create_match(
        self,
        rule: CorrelationRule,
        events: List[SecurityEvent],
        match_type: str,
        correlated_entities: Optional[Dict[str, List[str]]] = None
    ) -> CorrelationMatch:
        """Create a correlation match."""
        match_id = f"match_{uuid.uuid4().hex[:12]}"

        # Calculate confidence
        confidence = self._calculate_confidence(rule, events)

        # Build attack timeline
        timeline = []
        for event in sorted(events, key=lambda e: e.timestamp):
            timeline.append({
                "timestamp": event.timestamp.isoformat(),
                "source": event.source.value,
                "event_type": event.normalized.get("event_type"),
                "description": self._event_description(event),
                "mitre": event.mitre_techniques
            })

        # Determine severity
        base_severity = self._max_severity(events)
        severity_boost = rule.severity_boost
        severity = self._boost_severity(base_severity, severity_boost)

        match = CorrelationMatch(
            match_id=match_id,
            rule=rule,
            events=events,
            matched_at=datetime.now(),
            confidence=confidence,
            correlated_entities=correlated_entities or {},
            attack_timeline=timeline,
            severity=severity
        )

        # Store active match
        self.active_matches[match_id] = match
        self.match_history.append(match)

        # Keep history bounded
        if len(self.match_history) > 10000:
            self.match_history = self.match_history[-5000:]

        return match

    def _calculate_confidence(self, rule: CorrelationRule, events: List[SecurityEvent]) -> float:
        """Calculate confidence score for match."""
        base = 0.5

        # More events = higher confidence
        base += min(len(events) * 0.05, 0.3)

        # Multiple sources = higher confidence
        sources = set(e.source for e in events)
        base += len(sources) * 0.05

        # MITRE technique overlap
        all_techniques = set()
        for e in events:
            all_techniques.update(e.mitre_techniques)
        if all_techniques & set(rule.mitre_techniques):
            base += 0.15

        # Rule severity boost
        base += rule.severity_boost * 0.05

        return min(base, 0.99)

    def _max_severity(self, events: List[SecurityEvent]) -> str:
        """Get maximum severity from events."""
        severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        max_sev = "info"
        max_val = 0
        for e in events:
            val = severity_order.get(e.severity, 0)
            if val > max_val:
                max_val = val
                max_sev = e.severity
        return max_sev

    def _boost_severity(self, severity: str, boost: int) -> str:
        """Boost severity level."""
        severity_order = ["info", "low", "medium", "high", "critical"]
        idx = severity_order.index(severity) if severity in severity_order else 0
        new_idx = min(idx + boost, len(severity_order) - 1)
        return severity_order[new_idx]

    def _event_description(self, event: SecurityEvent) -> str:
        """Generate human-readable event description."""
        norm = event.normalized
        etype = norm.get("event_type", "event")
        host = norm.get("host", "unknown")
        user = norm.get("user", "")
        proc = norm.get("process", "")

        parts = [etype]
        if host:
            parts.append(f"on {host}")
        if user:
            parts.append(f"by {user}")
        if proc:
            parts.append(f"({proc})")

        return " ".join(parts)

    def get_active_matches(self, min_confidence: float = 0.0, min_severity: str = "info") -> List[CorrelationMatch]:
        """Get active correlation matches with filters."""
        severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        min_sev_val = severity_order.get(min_severity, 0)

        return [
            m for m in self.active_matches.values()
            if m.confidence >= min_confidence and severity_order.get(m.severity, 0) >= min_sev_val
        ]

    def get_match(self, match_id: str) -> Optional[CorrelationMatch]:
        """Get a specific match by ID."""
        return self.active_matches.get(match_id) or next((m for m in self.match_history if m.match_id == match_id), None)

    def acknowledge_match(self, match_id: str, analyst: str = "") -> bool:
        """Acknowledge a match (removes from active)."""
        if match_id in self.active_matches:
            match = self.active_matches.pop(match_id)
            match.acknowledged = True
            match.acknowledged_by = analyst
            match.acknowledged_at = datetime.now()
            return True
        return False

    def get_timeline(self, entity_type: str, entity_value: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get attack timeline for an entity."""
        cutoff = datetime.now() - timedelta(hours=hours)
        events = self.events_by_entity.get(entity_type, {}).get(entity_value, [])
        recent = [e for e in events if e.timestamp >= cutoff]
        recent.sort(key=lambda e: e.timestamp)

        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "source": e.source.value,
                "event_type": e.normalized.get("event_type"),
                "description": self._event_description(e),
                "severity": e.severity,
                "mitre": e.mitre_techniques
            }
            for e in recent
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_events": len(self.events),
            "active_matches": len(self.active_matches),
            "total_matches": len(self.match_history),
            "rules_loaded": len(self.rules),
            "events_by_source": {
                source.value: sum(1 for e in self.events if e.source == source)
                for source in EventSource
            },
            "entities_tracked": {
                etype: len(values) for etype, values in self.events_by_entity.items()
            }
        }


# Global instance
CORRELATION_ENGINE = ThreatCorrelationEngine()


async def correlate_events(
    events: List[Dict[str, Any]],
    source: str = "custom"
) -> List[Dict[str, Any]]:
    """Correlate a batch of events."""
    source_enum = EventSource(source) if source in [s.value for s in EventSource] else EventSource.CUSTOM

    results = []
    for evt_data in events:
        event = SecurityEvent(
            event_id=evt_data.get("event_id", ""),
            source=source_enum,
            timestamp=datetime.fromisoformat(evt_data["timestamp"]) if "timestamp" in evt_data else datetime.now(),
            raw_data=evt_data,
            severity=evt_data.get("severity", "info"),
            tags=evt_data.get("tags", [])
        )
        matches = CORRELATION_ENGINE.ingest_event(event)
        results.extend([{
            "match_id": m.match_id,
            "rule": m.rule.name,
            "confidence": m.confidence,
            "severity": m.severity,
            "timeline": m.attack_timeline
        } for m in matches])

    return results