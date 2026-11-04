import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.json_encoder import sanitize_for_json
from app.models.ask_data import ChatMessage, ConversationHistoryResponse


class ConversationService:
    """
    Manages dataset-isolated conversation sessions and history.
    Enforces snapshot hash synchronization so transformations (cleaning, undo, reset)
    do not contaminate analytical context.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.conv_dir = Path(base_dir or settings.UPLOAD_DIR) / "conversations"
        self.conv_dir.mkdir(parents=True, exist_ok=True)
        self.max_stored_messages = 30

    def _get_conv_path(self, dataset_id: str) -> Path:
        # Sanitize dataset_id to prevent directory traversal
        safe_id = Path(dataset_id).name.strip()
        return self.conv_dir / f"{safe_id}.json"

    def get_conversation(
        self, dataset_id: str, current_snapshot_hash: str
    ) -> ConversationHistoryResponse:
        """
        Loads conversation history for dataset.
        Checks snapshot hash synchronization.
        """
        path = self._get_conv_path(dataset_id)
        if not path.exists():
            return ConversationHistoryResponse(
                dataset_id=dataset_id,
                snapshot_hash=current_snapshot_hash,
                messages=[],
                total_messages=0,
                is_snapshot_synced=True,
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stored_hash = data.get("snapshot_hash", "")
            raw_msgs = data.get("messages", [])

            # Parse messages safely
            messages: List[ChatMessage] = []
            for m in raw_msgs:
                try:
                    messages.append(ChatMessage.model_validate(m))
                except Exception:
                    pass

            is_synced = stored_hash == current_snapshot_hash
            notice = None
            if not is_synced and len(messages) > 0:
                notice = "Dataset snapshot was modified (cleaning/undo/reset). Historical answers belong to the prior snapshot."

            return ConversationHistoryResponse(
                dataset_id=dataset_id,
                snapshot_hash=current_snapshot_hash,
                messages=messages,
                total_messages=len(messages),
                is_snapshot_synced=is_synced,
                notice=notice,
            )
        except Exception:
            return ConversationHistoryResponse(
                dataset_id=dataset_id,
                snapshot_hash=current_snapshot_hash,
                messages=[],
                total_messages=0,
                is_snapshot_synced=True,
            )

    def append_messages(
        self,
        dataset_id: str,
        current_snapshot_hash: str,
        new_messages: List[ChatMessage],
    ) -> None:
        """
        Appends new messages to conversation file atomically.
        """
        path = self._get_conv_path(dataset_id)
        existing_msgs: List[Dict[str, Any]] = []

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                existing_msgs = data.get("messages", [])
            except Exception:
                existing_msgs = []

        # Convert new messages to dictionaries
        for msg in new_messages:
            existing_msgs.append(msg.model_dump())

        # Bounding to max_stored_messages
        if len(existing_msgs) > self.max_stored_messages:
            existing_msgs = existing_msgs[-self.max_stored_messages :]

        now_iso = datetime.now(timezone.utc).isoformat()
        conv_payload = {
            "dataset_id": dataset_id,
            "snapshot_hash": current_snapshot_hash,
            "updated_at": now_iso,
            "messages": existing_msgs,
        }

        # Atomic write via temporary file
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(sanitize_for_json(conv_payload), f, indent=2)
            temp_path.replace(path)
        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def clear_conversation(self, dataset_id: str) -> bool:
        """
        Deletes stored conversation file for dataset.
        """
        path = self._get_conv_path(dataset_id)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception:
                return False
        return True

    def get_recent_context_for_prompt(
        self, dataset_id: str, current_snapshot_hash: str, max_turns: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves compact representation of the last N turns for question interpretation context.
        """
        conv = self.get_conversation(dataset_id, current_snapshot_hash)
        if not conv.messages:
            return []

        # Filter to recent turns
        recent = conv.messages[-(max_turns * 2) :]
        context = []
        for m in recent:
            item: Dict[str, Any] = {
                "role": m.role,
                "content": m.content,
            }
            if m.columns_used:
                item["columns_used"] = m.columns_used
            if m.calculation_method:
                item["calculation_method"] = m.calculation_method
            context.append(item)

        return context


# Global singleton instance
conversation_service = ConversationService()

