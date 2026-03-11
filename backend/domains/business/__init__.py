"""
Business Domain Module - Бизнес.

Анализ деловых встреч различных типов:
- Переговоры (Negotiations)
- Стратегическое планирование (Strategic Planning)
- Совет директоров (Board Meeting)
- Презентации (Presentations)
- Встречи с клиентами (Client Meetings)
"""
from .service import BusinessService
from .schemas import BusinessMeetingType, BusinessReport

__all__ = ["BusinessService", "BusinessMeetingType", "BusinessReport"]
