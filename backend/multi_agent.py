import asyncio
import logging
import time
import uuid
import json
import re
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

from model_router import ROUTER
from reasoning_engine import ReasoningEngine, ReasoningLevel
from plugins_system.runtime import PluginRuntime

log = logging.getLogger("MultiAgentOrchestrator")

class AgentTask:
    def __init__(self, task_id: str, title: str, detail: str, agent_role: str, priority: int = 0):
        self.task_id = task_id
        self.title = title
        self.detail = detail
        self.agent_role = agent_role
        self.priority = priority
        self.status = "pending"
        self.result: Any = None
        self.attempts = 0

class OrchestrationSession:
    def __init__(self, session_id: str, goal: str, reasoning_level: ReasoningLevel):
        self.session_id = session_id
        self.goal = goal
        self.reasoning_level = reasoning_level
        self.tasks: List[AgentTask] = []
        self.shared_context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.status = "active"
        self.created_at = time.time()

class MultiAgentOrchestrator:
    def __init__(self):
        self.reasoning_engine = ReasoningEngine()
        self.plugin_runtime = PluginRuntime()
        self.active_sessions: Dict[str, OrchestrationSession] = {}

    async def create_session(self, goal: str) -> str:
        level = await self.reasoning_engine.analyze_task(goal, [])
        session_id = f"orch_{uuid.uuid4().hex[:8]}"
        session = OrchestrationSession(session_id, goal, level)
        self.active_sessions[session_id] = session
        log.info(f"Session {session_id} created. Level: {level.name} | Goal: {goal[:50]}...")
        return session_id

    async def plan_tasks(self, session_id: str):
        session = self.active_sessions.get(session_id)
        if not session: 
            return
        
        log.info(f"Planning tasks for {session_id} at level {session.reasoning_level.name}")
        session.status = "planning"
        
        route, manager = await ROUTER.resolve("gemini-1.5-pro")
        if not manager:
            raise RuntimeError("Failed to acquire planner brain")

        planner_prompt = f"""
        GOAL: {session.goal}
        REASONING LEVEL: {session.reasoning_level.name}
        
        Decompose this goal into a precise sequence of sub-tasks.
        Assign a specialized ROLE to each: 'researcher', 'coder', 'tester', 'auditor', 'exploit', 'recon', 'summarizer'.
        
        Return ONLY a JSON array of objects.
        [
          {{"title": "task name", "detail": "detailed instruction", "agent": "role"}},
          ...
        ]
        """

        try:
            response = await manager.ainvoke([
                {"role": "system", "content": "You are a strategic planner. Output only valid JSON array."},
                {"role": "user", "content": planner_prompt}
            ])
            content = response.content
            
            match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
            if match:
                plan_data = json.loads(match.group(0))
                for i, item in enumerate(plan_data):
                    task = AgentTask(
                        task_id=f"t_{i}",
                        title=item['title'],
                        detail=item['detail'],
                        agent_role=item.get('agent', 'researcher')
                    )
                    session.tasks.append(task)
                session.status = "planned"
                log.info(f"Plan created: {len(session.tasks)} tasks for session {session_id}")
            else:
                raise ValueError(f"No JSON array found in response: {content[:100]}")
        except Exception as e:
            log.error(f"Planning failed for {session_id}: {e}")
            session.status = "failed"
            raise

    async def execute_session(self, session_id: str, user_id: str = "default_user") -> AsyncGenerator[Dict[str, Any], None]:
        session = self.active_sessions.get(session_id)
        if not session: 
            return
        
        if session.status != "planned":
            raise RuntimeError(f"Session {session_id} is in invalid state: {session.status}")

        session.status = "running"
        
        for task in session.tasks:
            if session.status in ("failed", "cancelled"):
                break
            
            task.status = "running"
            task.attempts += 1
            yield {"type": "task_start", "data": {"task_id": task.task_id, "title": task.title, "agent": task.agent_role}}

            try:
                route, brain = await self.get_brain_for_level(session.reasoning_level)
                
                context_summary = ""
                if session.history:
                    last_entries = session.history[-3:]
                    context_summary = "\n".join([f"[{h['role']}]: {h['content'][:200]}" for h in last_entries])
                
                shared_knowledge = json.dumps(session.shared_context, indent=2)

                task_prompt = f"""
                CURRENT SESSION GOAL: {session.goal}
                PAST ACTIONS/RESULTS:
                {context_summary if context_summary else "No previous history."}
                SHARED KNOWLEDGE (JSON):
                {shared_knowledge}

                CURRENT TASK:
                Role: {task.agent_role}
                Instruction: {task.detail}
                
                Respond with a JSON object containing 'result' (string) and 'updates' (dict of shared_context updates).
                """

                response = await brain.ainvoke([
                    {"role": "system", "content": f"You are an expert {task.agent_role} in a multi-agent swarm."},
                    {"role": "user", "content": task_prompt}
                ])

                content = response.content
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    result_data = json.loads(match.group(0))
                    task.result = result_data.get("result", content)
                    if isinstance(result_data.get("updates"), dict):
                        session.shared_context.update(result_data["updates"])
                    
                    task.status = "completed"
                    session.history.append({"role": "agent", "agent": task.agent_role, "task_id": task.task_id, "content": task.result})
                    yield {"type": "task_success", "data": {"task_id": task.task_id, "result": task.result}}
                else:
                    raise ValueError("Agent failed to return a JSON result object.")

            except Exception as e:
                log.error(f"Task {task.task_id} failed: {e}")
                task.status = "failed"
                session.status = "failed"
                yield {"type": "task_error", "data": {"task_id": task.task_id, "error": str(e)}}

session.status = "completed" if session.status != "failed" else "failed"
        yield {"type": "session_finished", "data": {"status": session.status, "final_context": session.shared_context}}

    async def get_brain_for_level(self, level: ReasoningLevel) -> tuple[Any, Any]:
        if level.value >= 4:
            return await ROUTER.resolve("gemini-1.5-pro")
        elif level.value >= 2:
            return await ROUTER.resolve("gpt-4o")
        else:
            return await ROUTER.resolve("groq")

    def get_session(self, session_id: str) -> Optional[OrchestrationSession]:
        return self.active_sessions.get(session_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return [{"session_id": s.session_id, "goal": s.goal, "status": s.status, "tasks_count": len(s.tasks), "reasoning_level": s.reasoning_level.name, "created_at": s.created_at} for s in self.active_sessions.values()]

    def cancel(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            self.active_sessions[session_id].status = "cancelled"
            return True
        return False
