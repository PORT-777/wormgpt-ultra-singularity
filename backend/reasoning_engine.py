"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Adaptive Reasoning Engine (L1-L5)
This module manages the cognitive depth required for a task.
L1: Instant/Reactive (Fast models)
L2: Standard (Balanced models)
L3: Deep Reasoning (High-intelligence models)
L4: Expert/Strategic (Complex tool-use, long context)
L5: Singularity (Self-correcting, multi-agent, recursive reasoning)
"""

import enum
import logging
from typing import Dict, Any, List, Optional

log = logging.getLogger("ReasoningEngine")

class ReasoningLevel(enum.IntEnum):
    L1_FAST = 1
    L2_STANDARD = 2
    L3_DEEP = 3
    L4_EXPERT = 4
    L5_SINGULARITY = 5

class ReasoningEngine:
    def __init__(self):
        self.level_thresholds = {
            "complexity_score": 0.0,
            "tool_dependency": 0,
            "context_size": 0
        }

    async def analyze_task(self, task_description: str, tools_available: List[str]) -> ReasoningLevel:
        """
        Analyte the task to determine the required cognitive level.
        """
        score = 0.0
        
        # 1. Complexity based on keyword density and structure
        complexity_keywords = {
            "compare": 0.5, "analyze": 1.0, "optimize": 1.5, "architect": 2.0,
            "exploit": 2.0, "audit": 1.5, "debug": 1.0, "implement": 1.0,
            "research": 0.8, "create": 0.5, "automate": 1.2, "remediate": 1.5,
            "secure": 1.5, "scan": 0.5, "find": 0.3, "fix": 1.0
        }
        
        desc = task_description.lower()
        for kw, weight in complexity_keywords.items():
            if kw in desc:
                score += weight

        # 2. Tool Dependency Analysis
        # More tool calls usually imply higher reasoning requirements
        tool_score = len(tools_available) * 0.1
        score += tool_score

        # 3. Special logic for L5 (Singularity)
        if "multi-step" in desc or "complex" in desc or "orchestrate" in desc:
            score += 5.0
        
        if "exploit" in desc or "vulnerability" in desc or "security" in desc:
            score += 2.0

        log.info(f"Task analyzed. Complexity score: {score:.2f}")

        # Map score to level
        if score < 2.0:
            return ReasoningLevel.L1_FAST
        elif score < 5.0:
            return ReasoningLevel.L2_STANDARD
        elif score < 8.0:
            return ReasoningLevel.L3_DEEP
        elif score < 12.0:
            return ReasoningLevel.L4_EXPERT
        else:
            return ReasoningLevel.L5_SINGULARITY

    def get_model_requirements(self, level: ReasoningLevel) -> Dict[str, Any]:
        """Returns model constraints and characteristics for a given level."""
        mapping = {
            ReasoningLevel.L1_FAST: {
                "min_intelligence": "low",
                "max_latency_ms": 500,
                "preferred_providers": ["groq", "deepseek"],
                "reasoning_style": "reactive"
            },
            ReasoningLevel.L2_STANDARD: {
                "min_intelligence": "medium",
                "max_latency_ms": 2000,
                "preferred_providers": ["openai", "mistral"],
                "reasoning_style": "iterative"
            },
            ReasoningLevel.L3_DEEP: {
                "min_intelligence": "high",
                "max_latency_ms": 10000,
                "preferred_providers": ["gemini", "anthropic"],
                "reasoning_style": "chain-of-thought"
            },
            ReasoningLevel.L4_EXPERT: {
                "min_intelligence": "very_high",
                "max_latency_ms": 30000,
                "preferred_providers": ["gemini", "openai", "anthropic"],
                "reasoning_style": "plan-and-execute"
            },
            ReasoningLevel.L5_SINGULARITY: {
                "min_intelligence": "extreme",
                "max_latency_ms": 120000,
                "preferred_providers": ["gemini", "openai"],
                "reasoning_style": "recursive_orchestration"
            }
        }
        return mapping.get(level, mapping[ReasoningLevel.L2_STANDARD])
