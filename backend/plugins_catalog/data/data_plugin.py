from typing import Any, Dict, List
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class DataIntelligencePlugin(BasePlugin):
    manifest = PluginManifest(
        id="data",
        name="Data Intelligence",
        description="Advanced data analysis, cleaning, and transformation",
        long_description=(
            "Data engineering capabilities: clean messy datasets, perform statistical "
            "analysis, transform formats (CSV to JSON), detect outliers, and generate "
            "summary reports from large text or structured data."
        ),
        version="1.0.0",
        author="outcome",
        icon="📊",
        category="data",
        tags=["data", "analysis", "statistics", "cleaning", "transform"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="data.clean",
                display_name="Clean Data",
                description="Remove duplicates and normalize text/numbers in a dataset",
                parameters={
                    "data": {"type": "array", "description": "List of objects or values"},
                    "remove_duplicates": {"type": "boolean"},
                },
            ),
            PluginTool(
                name="data.summarize",
                display_name="Summarize Dataset",
                description="Generate statistical summary (mean, median, min, max, count)",
                parameters={
                    "data": {"type": "array"},
                    "column": {"type": "string", "description": "Column to analyze"},
                },
            ),
            PluginTool(
                name="data.transform",
                display_name="Transform Format",
                description="Convert data between formats (CSV, JSON, Markdown)",
                parameters={
                    "data": {"type": "array"},
                    "target_format": {"type": "string", "description": "csv | json | markdown"},
                },
            ),
            PluginTool(
                name="data.detectOutliers",
                display_name="Detect Outliers",
                description="Identify anomalies in a numeric column using Z-score",
                parameters={
                    "data": {"type": "array"},
                    "column": {"type": "string"},
                    "threshold": {"type": "number", "description": "Z-score threshold, default 3.0"},
                },
            ),
        ],
        website_url="https://pandas.pydata.org",
        docs_url="https://pandas.pydata.org/docs/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        import math

        if tool_name == "data.clean":
            data = parameters.get("data", [])
            if not isinstance(data, list):
                raise ValueError("Data must be an array")
            
            if parameters.get("remove_duplicates"):
                # If it's a list of dicts, deduplicate by full content
                if data and isinstance(data[0], dict):
                    seen = set()
                    new_data = []
                    for item in data:
                        item_str = json.dumps(item, sort_keys=True)
                        if item_str not in seen:
                            seen.add(item_str)
                            new_data.append(item)
                    data = new_data
                else:
                    data = list(dict.fromkeys(data))
            return data

        if tool_name == "data.summarize":
            data = parameters.get("data", [])
            col = parameters.get("column")
            if not isinstance(data, list) or not data:
                return {"count": 0}
            
            vals = []
            if col:
                for item in data:
                    if isinstance(item, dict) and col in item:
                        val = item[col]
                        if isinstance(val, (int, float)):
                            vals.append(val)
            else:
                vals = [v for v in data if isinstance(v, (int, float))]

            if not vals:
                return {"count": len(data), "error": "no numeric column found"}

            return {
                "count": len(vals),
                "min": min(vals),
                "max": max(vals),
                "sum": sum(vals),
                "avg": sum(vals) / len(vals),
                "median": sorted(vals)[len(vals)//2],
            }

        if tool_name == "data.transform":
            import csv
            import io
            data = parameters.get("data", [])
            fmt = parameters.get("target_format", "json").lower()
            
            if fmt == "json":
                return data
            if fmt == "csv":
                if not data or not isinstance(data[0], dict):
                    raise ValueError("CSV transform requires array of dicts")
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue()
            if fmt == "markdown":
                if not data or not isinstance(data[0], dict):
                    raise ValueError("Markdown transform requires array of dicts")
                cols = list(data[0].keys())
                lines = [f"| {' | '.join(cols)} |", f"| {' | '.join(['---']*len(cols))} |"]
                for row in data:
                    lines.append(f"| {' | '.join(str(row.get(c, '')) for c in cols)} |")
                return "\n".join(lines)
            raise ValueError(f"Unsupported format: {fmt}")

        if tool_name == "data.detectOutliers":
            data = parameters.get("data", [])
            col = parameters.get("column")
            threshold = float(parameters.get("threshold", 3.0))
            
            if not col or not data or not isinstance(data[0], dict):
                raise ValueError("Requires array of dicts and a column name")
            
            vals = [float(item[col]) for item in data if col in item and isinstance(item[col], (int, float))]
            if len(vals) < 2:
                return {"outliers": [], "message": "Insufficient data"}
            
            mean = sum(vals) / len(vals)
            std_dev = (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5
            if std_dev == 0:
                return {"outliers": [], "message": "Zero variance"}

            outliers = []
            for idx, item in enumerate(data):
                val = item.get(col)
                if isinstance(val, (int, float)):
                    z = abs(val - mean) / std_dev
                    if z > threshold:
                        outliers.append({"index": idx, "value": val, "z_score": round(z, 2)})
            
            return {"count": len(outliers), "outliers": outliers}

        raise ValueError(f"Unknown data tool: {tool_name}")
