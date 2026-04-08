from sqlalchemy.orm import Session
from src.api import models
from src.model.model_manager import get_model_manager


class ConversationTitleService:
    @staticmethod
    async def generate_title(conversation_id: str, db: Session) -> str:
        # Fetch conversation and first few messages
        conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if not conversation:
            return "Untitled Conversation"

        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conversation_id
        ).order_by(models.Message.created_at.asc()).limit(5).all()

        if not messages:
            return "New Conversation"

        # Build prompt for title generation
        transcript = "\n".join([f"{msg.role}: {msg.content[:200]}" for msg in messages])
        prompt = (
            "Based on the following conversation transcript, generate a concise and descriptive title "
            "(max 6 words). Return ONLY the title text.\n\n"
            f"Transcript:\n{transcript}"
        )

        try:
            model_manager = get_model_manager()
            title = await model_manager.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20,
            )
            return title.strip().strip('"')
        except Exception:
            return messages[0].content[:30] + "..." if messages else "New Conversation"

    @staticmethod
    async def update_title(conversation_id: str, db: Session):
        title = await ConversationTitleService.generate_title(conversation_id, db)
        conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if conversation:
            conversation.title = title
            db.commit()
            db.refresh(conversation)
        return title
