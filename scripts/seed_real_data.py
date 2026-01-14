#!/usr/bin/env python3
"""
Seed real data from result_transcript.docx for Manager Dashboard.

Clears test data and creates one real report with Gemini-generated analytics.

Usage:
    docker exec whisperx-api python /app/scripts/seed_real_data.py
"""
import asyncio
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import uuid
import warnings

warnings.filterwarnings('ignore')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from docx import Document
import google.generativeai as genai

from backend.shared.database import async_session_factory, init_db
from backend.shared.models import User, project_managers
from backend.domains.construction.models import (
    ConstructionProject,
    ConstructionReportDB,
    ReportAnalytics,
    ReportProblem,
)
from backend.core.auth.dependencies import get_password_hash


# Gemini configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL_NAME', 'gemini-2.5-flash')


def extract_transcript(docx_path: str) -> str:
    """Extract text from docx file."""
    doc = Document(docx_path)
    return '\n'.join([p.text.strip() for p in doc.paragraphs if p.text.strip()])


def generate_analytics(transcript_text: str) -> dict:
    """Generate analytics using Gemini API."""
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not set, using mock data")
        return {
            "overall_status": "Требует внимания",
            "executive_summary": "Совещание по бытовому городку. Обсуждались вопросы планировки, водоснабжения и электроснабжения.",
            "dynamic_indicators": [
                {"indicator_name": "Проектная документация", "status": "В норме", "comment": "План расположения зданий согласован"},
                {"indicator_name": "Водоснабжение", "status": "В норме", "comment": "Параметры 90 л/с для пожаротушения приняты"},
                {"indicator_name": "Электроснабжение", "status": "Есть риски", "comment": "Общая мощность не утверждена"},
            ],
            "key_challenges": [
                {"id": 1, "problem": "Не утверждена общая мощность электропотребления", "ai_recommendation": "Запросить расчёт мощности", "status": "new"},
                {"id": 2, "problem": "Требуется формализация решений по водоснабжению", "ai_recommendation": "Подготовить протокол согласования", "status": "new"},
            ],
            "key_achievements": [
                {"achievement": "Согласован план расположения зданий с функциональным зонированием"},
                {"achievement": "Достигнуто согласие по параметрам пожарного водоснабжения (90 л/с)"},
            ],
            "toxicity_level": "Напряженный",
            "toxicity_comment": "Технические разногласия по нормативам, проблемы со связью у участников."
        }

    genai.configure(api_key=GEMINI_API_KEY)

    full_prompt = f'''Ты — опытный, уравновешенный и объективный руководитель проектов (технический заказчик). Твой анализ должен быть предельно взвешенным и фактологическим. Избегай драматизации, паники и гипотез. Твоя задача — предоставить трезвую оценку ситуации.

Проанализируй стенограмму совещания по строительному проекту. Твоя цель — извлечь ключевые бизнес-сигналы и представить их в виде структурированного JSON-отчета по схеме ManagerAnalyticsConstruction.

# ПРАВИЛА И СТРУКТУРА ВЫВОДА (JSON)
0. **ИНОСТРАННЫЕ ПАРТНЕРЫ**: Если говорят на иностранном языке (EN/ZH), анализируй смысл сказанного. В отчет пиши ТОЛЬКО НА РУССКОМ.
1. **Строгое определение статусов**: Для поля overall_status используй:
    - "Стабильный": Серьезных отклонений от плана нет, риски управляемы.
    - "Требует внимания": Есть потенциальные риски, отставания или проблемы, но пока не критичны.
    - "Критический": ТОЛЬКО ЕСЛИ прямая угроза срыва сроков/бюджета, работа заблокирована.
2. **Конструктивный подход**: В key_challenges предлагай решение в ai_recommendation.
3. **Сбалансированность**: В key_achievements найди 1-2 положительных момента.
4. **executive_summary**: Выжимка для руководителя (2-3 предложения).
5. **dynamic_indicators**: Список из 3-5 показателей с полями indicator_name, status ("В норме", "Есть риски", "Критический") и comment.
6. **key_challenges**: Список из 2-3 проблем с полями id, problem, ai_recommendation и status ("new").
7. **key_achievements**: Список из 1-2 достижений с полем achievement.
8. **toxicity_level**: "Высокий", "Напряженный" или "Нейтральный".
9. **toxicity_comment**: Обоснование оценки конфликтности.

Вот стенограмма для анализа:
---
{transcript_text}
---'''

    print(f"Calling Gemini API ({GEMINI_MODEL})...")
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        full_prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type='application/json',
            temperature=0.3,
        )
    )

    return json.loads(response.text)


async def clear_test_data(session):
    """Clear all test data from database."""
    print("Clearing test data...")

    # Delete in correct order due to foreign keys
    await session.execute(delete(ReportProblem))
    await session.execute(delete(ReportAnalytics))
    await session.execute(delete(ConstructionReportDB))
    await session.execute(delete(project_managers))
    await session.execute(delete(ConstructionProject))

    await session.commit()
    print("Test data cleared")


async def seed_real_data():
    """Seed real data from transcript."""
    await init_db()

    print("\n" + "=" * 60)
    print("SEEDING REAL DATA FROM TRANSCRIPT")
    print("=" * 60 + "\n")

    # Extract transcript
    transcript_path = "/app/result_transcript.docx"
    if not os.path.exists(transcript_path):
        print(f"ERROR: Transcript file not found: {transcript_path}")
        return

    transcript_text = extract_transcript(transcript_path)
    print(f"Transcript extracted: {len(transcript_text)} chars")

    # Generate analytics with Gemini
    analytics_data = generate_analytics(transcript_text)
    print("Analytics generated successfully")
    print(json.dumps(analytics_data, indent=2, ensure_ascii=False)[:500] + "...")

    async with async_session_factory() as session:
        # Clear existing test data
        await clear_test_data(session)

        # Get manager user
        result = await session.execute(
            select(User).where(User.role == "manager")
        )
        manager = result.scalar_one_or_none()

        if not manager:
            print("Creating manager user...")
            manager = User(
                username="manager",
                email="manager@dev.local",
                hashed_password=get_password_hash("devpassword"),
                role="manager",
                full_name="Иван Петров",
                is_active=True,
            )
            session.add(manager)
            await session.flush()

        # Create real project
        project = ConstructionProject(
            name="Бытовой городок PowerChina",
            description="Проектирование и строительство бытового городка для рабочих",
            project_code="2001",
            is_active=True,
        )
        session.add(project)
        await session.flush()
        print(f"Created project: {project.name} (code={project.project_code})")

        # Assign manager to project
        await session.execute(
            project_managers.insert().values(
                user_id=manager.id,
                project_id=project.id,
            )
        )

        # Map overall_status to health
        status_map = {
            "Стабильный": "stable",
            "Требует внимания": "attention",
            "Критический": "critical",
        }
        health = status_map.get(analytics_data.get("overall_status", ""), "attention")

        # Create report
        report = ConstructionReportDB(
            project_id=project.id,
            job_id=str(uuid.uuid4()),
            title="Совещание по бытовому городку ПОС",
            audio_file_path="2025-12-02_совещание Кравт, Северин, Powerchina_Бытов.городок ПОС.mp4",
            status="completed",
            meeting_date=datetime(2025, 12, 2),
            created_at=datetime.now(),
        )
        session.add(report)
        await session.flush()
        print(f"Created report: {report.title}")

        # Map toxicity level to numeric
        toxicity_map = {
            "Нейтральный": 20,
            "Напряженный": 50,
            "Высокий": 80,
        }
        toxicity_level = toxicity_map.get(analytics_data.get("toxicity_level", ""), 30)
        toxicity_details = f"{analytics_data.get('toxicity_level', 'Нейтральный')}\n\n{analytics_data.get('toxicity_comment', '')}"

        # Create analytics
        analytics = ReportAnalytics(
            report_id=report.id,
            summary=analytics_data.get("executive_summary", ""),
            health_status=health,
            key_indicators=analytics_data.get("dynamic_indicators", []),
            challenges=[
                {"text": c["problem"], "recommendation": c["ai_recommendation"]}
                for c in analytics_data.get("key_challenges", [])
            ],
            achievements=[a["achievement"] for a in analytics_data.get("key_achievements", [])],
            toxicity_level=toxicity_level,
            toxicity_details=toxicity_details,
        )
        session.add(analytics)
        await session.flush()
        print(f"Created analytics (id={analytics.id})")

        # Create problems from key_challenges
        for challenge in analytics_data.get("key_challenges", []):
            # Map status string
            severity = "critical" if "критич" in challenge.get("problem", "").lower() else "attention"

            problem = ReportProblem(
                analytics_id=analytics.id,
                problem_text=challenge["problem"],
                recommendation=challenge["ai_recommendation"],
                status="new",
                severity=severity,
            )
            session.add(problem)

        await session.commit()
        print(f"Created {len(analytics_data.get('key_challenges', []))} problems")

    print("\n" + "=" * 60)
    print("REAL DATA SEEDED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nCreated:")
    print(f"  - 1 project: Бытовой городок PowerChina (2001)")
    print(f"  - 1 report with real analytics from Gemini")
    print(f"\nLogin as manager@dev.local / devpassword to view dashboard")


if __name__ == "__main__":
    asyncio.run(seed_real_data())
