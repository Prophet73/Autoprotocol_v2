"""
Shared Pydantic models reused across business and dct domains.

Brainstorm and Lecture schemas are structurally identical in both domains.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# Brainstorm schemas (shared by business + dct)
# =============================================================================

class BrainstormIdeaCluster(BaseModel):
    """Кластер идей."""
    cluster_name: str = Field(..., description="Название направления/кластера")
    ideas: List[str] = Field(default_factory=list, description="Список идей в кластере")


class BrainstormTopIdea(BaseModel):
    """Перспективная идея."""
    idea_description: str = Field(..., description="Описание идеи")
    potential_impact: Optional[str] = Field(None, description="Потенциальное влияние: Высокий/Средний/Низкий")
    implementation_complexity: Optional[str] = Field(None, description="Сложность реализации: Высокая/Средняя/Низкая")


class BrainstormNextStep(BaseModel):
    """Следующий шаг после мозгового штурма."""
    action_item: str = Field(..., description="Что нужно сделать")
    responsible: Optional[str] = Field(None, description="Ответственный")
    deadline: Optional[str] = Field(None, description="Срок")


# =============================================================================
# Lecture schemas (shared by business + dct)
# =============================================================================

class LectureBlock(BaseModel):
    """Блок из основной части лекции."""
    block_title: str = Field(..., description="Название блока")
    time_code: Optional[str] = Field(None, description="Тайм-код")
    key_idea: Optional[str] = Field(None, description="Ключевая мысль")
    theses: List[str] = Field(default_factory=list, description="Тезисы")


class LectureQA(BaseModel):
    """Вопрос-ответ из Q&A сессии."""
    question_title: str = Field(..., description="Вопрос")
    time_code: Optional[str] = Field(None, description="Тайм-код")
    key_answer_idea: Optional[str] = Field(None, description="Ключевая мысль ответа")
    answer_theses: List[str] = Field(default_factory=list, description="Тезисы ответа")


class LectureResult(BaseModel):
    """Результаты конспекта лекции/вебинара."""
    webinar_title: Optional[str] = Field(None, description="Название вебинара/лекции")
    presentation_part: List[LectureBlock] = Field(default_factory=list, description="Основная часть")
    qa_part: List[LectureQA] = Field(default_factory=list, description="Сессия Q&A")
    final_summary: List[str] = Field(default_factory=list, description="Итоговые выводы")
