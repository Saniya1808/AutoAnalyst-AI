import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query
import pandas as pd

from app.core.config import settings
from app.core.json_encoder import sanitize_for_json
from app.models.ask_data import (
    AskDataRequest,
    AskDataResponse,
    ChatMessage,
    ConversationHistoryResponse,
    SuggestedPromptsResponse,
)
from app.services.ai.analytical_executor import AnalyticalExecutor
from app.services.ai.answer_generator import AnswerGenerator
from app.services.ai.conversation_service import conversation_service
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.question_interpreter import QuestionInterpreter
from app.services.dataset_storage import dataset_storage
from app.services.profiler import infer_column_type

router = APIRouter(prefix="/datasets", tags=["Ask Your Data"])


@router.post("/{dataset_id}/ask", response_model=AskDataResponse)
async def ask_dataset_question(
    dataset_id: str,
    request: AskDataRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> AskDataResponse:
    """
    Submits a natural language question against the selected dataset.
    Interprets intent, executes safe Pandas computation, grounds facts, and returns explanation.
    """
    clean_id = f"clean_{dataset_id}"
    has_clean = dataset_storage.get_dataset(clean_id) is not None
    active_id = clean_id if has_clean else dataset_id
    detail = dataset_storage.get_authorized_dataset(active_id, session_id=x_session_id)

    file_path = dataset_storage.get_dataset_file_path(active_id)
    snapshot_hash = dataset_storage.compute_sha256(file_path)

    # 1. Load DataFrame safely
    try:
        df = dataset_storage._load_dataframe(active_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {str(e)}")

    # 2. Retrieve recent conversation context
    recent_context = conversation_service.get_recent_context_for_prompt(
        dataset_id=dataset_id,
        current_snapshot_hash=snapshot_hash,
        max_turns=3,
    )

    # 3. Initialize LLM Provider if configured
    api_key = settings.effective_gemini_api_key
    provider = GeminiProvider(api_key=api_key, model_name=settings.AI_MODEL_NAME) if api_key else None

    # 4. Interpret question into QueryPlan
    plan, interp_mode = await QuestionInterpreter.interpret_question(
        question=request.question,
        columns=detail.columns,
        row_count=detail.overview.row_count,
        provider=provider,
        recent_messages=recent_context,
        timeout_seconds=settings.AI_TIMEOUT_SECONDS,
    )

    # If chart not requested by user, strip chart recommendation
    if not request.include_chart and plan.chart:
        plan.chart.chart_type = "none"

    # 5. Execute Plan via hardened Pandas Analytical Executor
    calc_result = AnalyticalExecutor.execute_plan(df=df, plan=plan, dataset_id=dataset_id)

    # 6. Synthesize grounded answer
    direct_answer, follow_ups, answer_mode = await AnswerGenerator.generate_answer(
        question=request.question,
        plan=plan,
        calc_result=calc_result,
        provider=provider,
        timeout_seconds=settings.AI_TIMEOUT_SECONDS,
    )

    final_mode = "ai_generated" if (interp_mode == "ai_generated" and answer_mode == "ai_generated") else "statistical_fallback"
    effective_model = settings.AI_MODEL_NAME if final_mode == "ai_generated" else "Deterministic Heuristics Engine"
    effective_provider = "gemini" if final_mode == "ai_generated" else "fallback"

    now_iso = datetime.now(timezone.utc).isoformat()
    user_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    assistant_msg_id = f"msg_{uuid.uuid4().hex[:10]}"

    user_msg = ChatMessage(
        message_id=user_msg_id,
        role="user",
        content=request.question,
        created_at=now_iso,
        dataset_id=dataset_id,
        snapshot_hash=snapshot_hash,
    )

    assistant_msg = ChatMessage(
        message_id=assistant_msg_id,
        role="assistant",
        content=direct_answer,
        created_at=now_iso,
        dataset_id=dataset_id,
        snapshot_hash=snapshot_hash,
        direct_answer=direct_answer,
        primary_metric=calc_result.primary_metric,
        calculation_method=calc_result.calculation_method,
        columns_used=calc_result.columns_used,
        filters_applied=calc_result.filters_applied,
        tabular_data=calc_result.tabular_data,
        chart=calc_result.chart,
        grounded_facts=calc_result.grounded_facts,
        limitations_and_warnings=calc_result.limitations_and_warnings,
        is_ambiguous=plan.is_ambiguous,
        clarification_prompt=plan.clarification_reason if plan.is_ambiguous else None,
        suggested_follow_ups=follow_ups,
        mode=final_mode,
        provider=effective_provider,
        model=effective_model,
    )

    # 7. Persist messages to isolated conversation history
    conversation_service.append_messages(
        dataset_id=dataset_id,
        current_snapshot_hash=snapshot_hash,
        new_messages=[user_msg, assistant_msg],
    )

    response_payload = AskDataResponse(
        message_id=assistant_msg_id,
        dataset_id=dataset_id,
        snapshot_hash=snapshot_hash,
        question=request.question,
        direct_answer=direct_answer,
        primary_metric=calc_result.primary_metric,
        calculation_method=calc_result.calculation_method,
        columns_used=calc_result.columns_used,
        filters_applied=calc_result.filters_applied,
        tabular_data=calc_result.tabular_data,
        chart=calc_result.chart,
        grounded_facts=calc_result.grounded_facts,
        limitations_and_warnings=calc_result.limitations_and_warnings,
        is_ambiguous=plan.is_ambiguous,
        clarification_prompt=plan.clarification_reason if plan.is_ambiguous else None,
        suggested_follow_ups=follow_ups,
        mode=final_mode,
        provider=effective_provider,
        model=effective_model,
        created_at=now_iso,
    )

    return sanitize_for_json(response_payload)


@router.get("/{dataset_id}/conversation", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> ConversationHistoryResponse:
    """
    Retrieves conversational chat history for a dataset.
    """
    clean_id = f"clean_{dataset_id}"
    has_clean = dataset_storage.get_dataset(clean_id) is not None
    active_id = clean_id if has_clean else dataset_id
    detail = dataset_storage.get_authorized_dataset(active_id, session_id=x_session_id)

    file_path = dataset_storage.get_dataset_file_path(active_id)
    snapshot_hash = dataset_storage.compute_sha256(file_path)

    history = conversation_service.get_conversation(
        dataset_id=dataset_id,
        current_snapshot_hash=snapshot_hash,
    )
    return sanitize_for_json(history)


@router.delete("/{dataset_id}/conversation")
async def clear_conversation(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> Dict[str, Any]:
    """
    Clears conversational chat history for a dataset.
    """
    clean_id = f"clean_{dataset_id}"
    has_clean = dataset_storage.get_dataset(clean_id) is not None
    active_id = clean_id if has_clean else dataset_id
    detail = dataset_storage.get_authorized_dataset(active_id, session_id=x_session_id)

    conversation_service.clear_conversation(dataset_id)
    return {"success": True, "message": f"Conversation history for dataset {dataset_id} cleared."}


@router.get("/{dataset_id}/suggested-questions", response_model=SuggestedPromptsResponse)
async def get_suggested_questions(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> SuggestedPromptsResponse:
    """
    Returns smart suggested analytical questions based on dataset schema.
    """
    clean_id = f"clean_{dataset_id}"
    has_clean = dataset_storage.get_dataset(clean_id) is not None
    active_id = clean_id if has_clean else dataset_id
    detail = dataset_storage.get_authorized_dataset(active_id, session_id=x_session_id)

    columns = detail.columns
    numeric_cols = [c.name for c in columns if c.data_type in ("integer", "float")]
    cat_cols = [c.name for c in columns if c.data_type in ("string", "boolean")]
    date_cols = [c.name for c in columns if c.data_type == "datetime"]

    prompts: List[str] = []

    # 1. Basic numeric aggregation
    if numeric_cols:
        prompts.append(f"What is the average {numeric_cols[0]}?")
    # 2. Group by comparison
    if numeric_cols and cat_cols:
        prompts.append(f"Compare {numeric_cols[0]} across {cat_cols[0]}.")
    # 3. Categorical distribution
    if cat_cols:
        prompts.append(f"What is the distribution of {cat_cols[0]}?")
    # 4. Correlation
    if len(numeric_cols) >= 2:
        prompts.append(f"Is there a correlation between {numeric_cols[0]} and {numeric_cols[1]}?")
    # 5. Trend
    if date_cols and numeric_cols:
        prompts.append(f"Show {numeric_cols[0]} trend over {date_cols[0]}.")
    # 6. Quality
    prompts.append("Which columns have missing values?")
    # 7. Ranking
    if numeric_cols:
        prompts.append(f"What are the top 5 records by {numeric_cols[0]}?")

    return SuggestedPromptsResponse(dataset_id=dataset_id, prompts=prompts[:6])

