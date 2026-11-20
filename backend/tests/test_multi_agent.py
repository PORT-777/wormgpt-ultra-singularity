import asyncio
import pytest
from multi_agent import MultiAgentOrchestrator, AgentTask, OrchestrationSession
from reasoning_engine import ReasoningLevel
from model_router import ROUTER
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_orchestrator_lifecycle():
    # Mock dependencies
    orchestrator = MultiAgentOrchestrator()
    
    # Mock ReasoningEngine.analyze_task
    orchestrator.reasoning_engine.analyze_task = AsyncMock(return_value=ReasoningLevel.L2_STANDARD)
    
    # Mock ROUTER.get_brain
    mock_brain = AsyncMock()
    mock_brain.ainvoke.return_value = MagicMock(content='{"result": "success", "updates": {"key": "val"}}')
    
    async def mock_get_brain(name):
        return mock_brain, mock_brain
    
    # We use a patch-like replacement since ROUTER is a global singleton in many places
    import model_router
    original_get_brain = ROUTER.get_brain
    ROUTER.get_brain = mock_get_brain

    try:
        # 1. Create Session
        session_id = await orchestrator.create_session("test goal")
        session = orchestrator.get_session(session_id)
        assert session.session_id == session_id
        assert session.status == "active"

        # 2. Plan Tasks
        await orchestrator.plan_tasks(session_id)
        assert session.status == "planned"
        assert len(session.tasks) > 0
        assert session.tasks[0].agent_role in ["researcher", "coder", "tester", "auditor", "exploit", "recon", "summarizer"]

        # 3. Execute Session
        gen = orchestrator.execute_session(session_id, user_id="test_user")
        results = []
        async for update in gen:
            results.append(update)

        assert len(results) >= 2  # At least task_start and task_success/error
        assert session.status == "completed"
        assert session.shared_context
    finally:
        ROUTER.get_brain = original_get_brain

@pytest.mark.asyncio
async def test_orchestrator_failure_handling():
    orchestrator = MultiAgentOrchestrator()
    orchestrator.reasoning_engine.analyze_task = AsyncMock(return_value=ReasoningLevel.L1_FAST)
    
    session_id = await orchestrator.create_session("fail goal")
    
    with pytest.raises(Exception, match="Planning exploded"):
        await orchestrator.plan_tasks(session_id)
    
    session = orchestrator.get_session(session_id)
    assert session.status == "failed"
