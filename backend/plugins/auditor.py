import time
import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger("PluginAuditor")

class PluginAuditor:
    """
    Advanced auditing engine for plugin telemetry, security, and performance.
    Tracks execution metrics, security anomalies, and usage patterns.
    """
    def __init__(self, db):
        self.db = db

    async def record_telemetry(
        self, 
        user_id: str, 
        plugin_id: str, 
        tool_name: str, 
        parameters: Dict[str, Any], 
        status: str, 
        duration_ms: float,
        error_details: Optional[str] = None
    ):
        """
        Records a complete telemetry snapshot for a tool execution.
        """
        audit_entry = {
            "user_id": user_id,
            "plugin_id": plugin_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "status": status,
            "duration_ms": duration_ms,
            "error_details": error_details,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # 1. Persistent storage for auditing
            await self.db.insert_plugin_usage_log(audit_entry)

            # 2. Real-time Security Monitoring
            if status == "error":
                await self._analyze_security_anomaly(audit_entry)
            
            # 3. Performance Monitoring
            if duration_ms > 5000:  # Threshold for slow tools
                logger.warning(f"SLOW PLUGIN DETECTED: {plugin_id}.{tool_name} took {duration_ms}ms")
                await self._log_performance_degradation(plugin_id, tool_name, duration_ms)

        except Exception as e:
            logger.error(f"Failed to record plugin telemetry: {str(e)}")

    async def _analyze_security_anomaly(self, entry: Dict[str, Any]):
        """
        Detects suspicious patterns such as credential probing or parameter injection attempts.
        """
        params_str = str(entry.get("parameters", "")).lower()
        
        # Simple heuristic for injection/probing patterns
        suspicious_patterns = ["'", "--", "drop table", "select *", "<script>", "../"]
        
        if any(pattern in params_str for pattern in suspicious_patterns):
            logger.critical(f"SECURITY ANOMALY DETECTED: Potential injection attempt in {entry['plugin_id']}.{entry['tool_name']}")
            await self.db.create_security_alert({
                "type": "PLUGIN_INJECTION_ATTEMPT",
                "severity": "HIGH",
                "user_id": entry["user_id"],
                "plugin_id": entry["plugin_id"],
                "tool_name": entry["tool_name"],
                "payload": entry["parameters"],
                "timestamp": entry["timestamp"]
            })

    async def _log_performance_degradation(self, plugin_id: str, tool_name: str, duration: float):
        """Logs performance degradation for system optimization."""
        await self.db.update_plugin_metrics(
            plugin_id=plugin_id,
            tool_name=tool_name,
            latency=duration
        )

    async def get_usage_report(self, user_id: str) -> Dict[str, Any]:
        """Generates a summary report of user plugin activity."""
        return await self.db.get_user_plugin_usage_summary(user_id)

