"""
Prompt template and AI schema generation service.

Provides:
- CRUD operations for prompt templates
- AI-powered JSON Schema generation using Gemini
- Schema validation for Gemini compatibility
"""
import os
import json
import logging
import re
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin.models import PromptTemplate
from .schemas import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
    GenerateSchemaRequest,
    GeneratedSchemaResponse,
    ValidateSchemaRequest,
    ValidateSchemaResponse,
    SchemaTemplateInfo,
    SchemaTemplatesResponse,
    SCHEMA_TEMPLATES,
)

logger = logging.getLogger(__name__)

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"


class PromptService:
    """Service for prompt template management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(
        self,
        data: PromptTemplateCreate,
        created_by: Optional[str] = None,
    ) -> PromptTemplate:
        """Create a new prompt template."""
        # Check if slug already exists
        existing = await self.get_template_by_slug(data.slug)
        if existing:
            raise ValueError(f"Template with slug '{data.slug}' already exists")

        # If setting as default, unset other defaults for this domain
        if data.is_default:
            await self._unset_domain_defaults(data.domain)

        template = PromptTemplate(
            name=data.name,
            slug=data.slug,
            domain=data.domain,
            description=data.description,
            system_prompt=data.system_prompt,
            user_prompt_template=data.user_prompt_template,
            response_schema=data.response_schema,
            is_default=data.is_default,
            created_by=created_by,
        )

        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: int) -> Optional[PromptTemplate]:
        """Get template by ID."""
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_template_by_slug(self, slug: str) -> Optional[PromptTemplate]:
        """Get template by slug."""
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_default_template(self, domain: str) -> Optional[PromptTemplate]:
        """Get default template for a domain."""
        result = await self.db.execute(
            select(PromptTemplate).where(
                and_(
                    PromptTemplate.domain == domain,
                    PromptTemplate.is_default == True,
                    PromptTemplate.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        domain: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> PromptTemplateListResponse:
        """List prompt templates with filtering."""
        query = select(PromptTemplate)

        if domain:
            query = query.where(PromptTemplate.domain == domain)
        if is_active is not None:
            query = query.where(PromptTemplate.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(
            PromptTemplate.domain,
            PromptTemplate.name,
        )
        result = await self.db.execute(query)
        templates = result.scalars().all()

        return PromptTemplateListResponse(
            templates=[PromptTemplateResponse.model_validate(t) for t in templates],
            total=total,
        )

    async def update_template(
        self,
        template_id: int,
        data: PromptTemplateUpdate,
    ) -> Optional[PromptTemplate]:
        """Update a prompt template."""
        template = await self.get_template(template_id)
        if not template:
            return None

        # If setting as default, unset other defaults
        if data.is_default:
            await self._unset_domain_defaults(template.domain, exclude_id=template_id)

        if data.name is not None:
            template.name = data.name
        if data.description is not None:
            template.description = data.description
        if data.system_prompt is not None:
            template.system_prompt = data.system_prompt
        if data.user_prompt_template is not None:
            template.user_prompt_template = data.user_prompt_template
        if data.response_schema is not None:
            template.response_schema = data.response_schema
        if data.is_active is not None:
            template.is_active = data.is_active
        if data.is_default is not None:
            template.is_default = data.is_default

        # Increment version on update
        template.version += 1

        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: int) -> bool:
        """Delete a prompt template."""
        template = await self.get_template(template_id)
        if not template:
            return False

        await self.db.delete(template)
        await self.db.flush()
        return True

    async def _unset_domain_defaults(
        self,
        domain: str,
        exclude_id: Optional[int] = None,
    ) -> None:
        """Unset is_default for all templates in a domain."""
        query = select(PromptTemplate).where(
            and_(
                PromptTemplate.domain == domain,
                PromptTemplate.is_default == True,
            )
        )
        if exclude_id:
            query = query.where(PromptTemplate.id != exclude_id)

        result = await self.db.execute(query)
        for template in result.scalars().all():
            template.is_default = False

        await self.db.flush()


class SchemaGeneratorService:
    """
    AI-powered JSON Schema generator using Gemini.

    Uses Gemini structured output to generate valid JSON Schemas
    from natural language descriptions.
    """

    # Meta-prompt for schema generation
    SCHEMA_GENERATOR_SYSTEM_PROMPT = """Ты — Системный Архитектор, специализирующийся на проектировании структур данных.

Твоя задача: преобразовать описание пользователя в валидную JSON Schema, совместимую с Gemini API.

## Правила JSON Schema для Gemini:

### Поддерживаемые типы:
- string: текстовые данные
- number: числа с плавающей точкой
- integer: целые числа
- boolean: true/false
- object: вложенные объекты
- array: массивы

### Поддерживаемые свойства:
- type: тип данных (обязательно)
- description: описание поля (ОЧЕНЬ ВАЖНО для качества)
- properties: свойства объекта
- required: массив обязательных полей
- items: схема элементов массива
- enum: ограниченный список значений (для string)
- format: формат (date, date-time, email, uri)
- minimum/maximum: для чисел
- minItems/maxItems: для массивов

### Лучшие практики:
1. ВСЕГДА добавляй description для каждого поля
2. Используй snake_case для имён полей
3. Указывай required для важных полей
4. Используй enum для ограниченных списков значений
5. Для дат используй format: "date" или "date-time"
6. Группируй связанные данные в объекты

### Пример хорошей схемы:
{
  "type": "object",
  "properties": {
    "meeting_summary": {
      "type": "string",
      "description": "Краткое резюме совещания"
    },
    "decisions": {
      "type": "array",
      "description": "Список принятых решений",
      "items": {
        "type": "object",
        "properties": {
          "decision": {"type": "string", "description": "Текст решения"},
          "responsible": {"type": "string", "description": "Ответственный"}
        },
        "required": ["decision"]
      }
    },
    "status": {
      "type": "string",
      "enum": ["stable", "attention", "critical"],
      "description": "Общий статус проекта"
    }
  },
  "required": ["meeting_summary", "decisions"]
}"""

    SCHEMA_GENERATOR_USER_PROMPT = """Создай JSON Schema для следующего описания:

**Описание:** {description}

**Тип выхода:** {output_type}

**Дополнительные требования:**
- Язык описаний полей: {language}
- Включить метаданные (title, date): {include_metadata}
{explicit_properties}

Верни только валидную JSON Schema в формате JSON. Без дополнительных пояснений."""

    def __init__(self):
        self.api_key = GEMINI_API_KEY

    async def generate_schema(
        self,
        request: GenerateSchemaRequest,
    ) -> GeneratedSchemaResponse:
        """
        Generate JSON Schema from natural language description.

        Uses Gemini to interpret the description and produce
        a valid, Gemini-compatible JSON Schema.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not configured")

        # Build explicit properties section
        explicit_props = ""
        if request.properties:
            props_list = []
            for prop in request.properties:
                prop_desc = f"  - {prop.name}: {prop.description}"
                if prop.type_hint:
                    prop_desc += f" (тип: {prop.type_hint})"
                if prop.enum_values:
                    prop_desc += f" [варианты: {', '.join(prop.enum_values)}]"
                if prop.required:
                    prop_desc += " [обязательное]"
                props_list.append(prop_desc)
            explicit_props = "\n**Явно указанные поля:**\n" + "\n".join(props_list)

        # Format user prompt
        user_prompt = self.SCHEMA_GENERATOR_USER_PROMPT.format(
            description=request.description,
            output_type=request.output_type or "report",
            language="русский" if request.language == "ru" else request.language,
            include_metadata="да" if request.include_metadata else "нет",
            explicit_properties=explicit_props,
        )

        try:
            # Call Gemini API
            schema_json = await self._call_gemini(
                system_prompt=self.SCHEMA_GENERATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            # Parse and validate the response
            schema = self._parse_schema_response(schema_json)

            # Validate for Gemini compatibility
            validation = self.validate_schema(schema)
            if not validation.valid:
                logger.warning(f"Generated schema has issues: {validation.errors}")

            # Generate schema name from description
            schema_name = self._generate_schema_name(request.description)

            # Generate example output
            example = self._generate_example(schema)

            return GeneratedSchemaResponse(
                schema=schema,
                schema_name=schema_name,
                description=request.description[:200],
                example_output=example,
                validation_status="valid" if validation.valid else "warnings",
                gemini_model=GEMINI_MODEL,
            )

        except Exception as e:
            logger.exception(f"Schema generation failed: {e}")
            raise ValueError(f"Failed to generate schema: {str(e)}")

    async def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Call Gemini API for schema generation."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,  # Low temperature for consistent output
                    response_mime_type="application/json",
                ),
            )

            return response.text

        except ImportError:
            # Fallback to REST API if google-genai not available
            return await self._call_gemini_rest(system_prompt, user_prompt)

    async def _call_gemini_rest(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Fallback: Call Gemini via REST API."""
        import httpx

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                params={"key": self.api_key},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            # Extract text from response
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _parse_schema_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON Schema from Gemini response."""
        # Try to parse as JSON directly
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        brace_start = response.find("{")
        brace_end = response.rfind("}")
        if brace_start != -1 and brace_end != -1:
            try:
                return json.loads(response[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError("Could not parse JSON Schema from response")

    def _generate_schema_name(self, description: str) -> str:
        """Generate a schema name from description."""
        # Extract key words
        words = description.lower().split()[:5]
        # Filter common words
        stop_words = {"i", "need", "want", "a", "an", "the", "for", "with", "and", "or",
                      "мне", "нужен", "нужна", "нужно", "для", "с", "и", "или"}
        words = [w for w in words if w not in stop_words]
        # Create snake_case name
        name = "_".join(words[:3]) if words else "custom_schema"
        return re.sub(r"[^a-z0-9_]", "", name)

    def _generate_example(self, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate an example output based on schema."""
        try:
            return self._generate_example_value(schema)
        except Exception as e:
            logger.debug(f"Failed to generate example output from schema: {e}")
            return None

    def _generate_example_value(self, schema: Dict[str, Any]) -> Any:
        """Recursively generate example values."""
        schema_type = schema.get("type", "string")

        if schema_type == "object":
            result = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                result[prop_name] = self._generate_example_value(prop_schema)
            return result

        elif schema_type == "array":
            items_schema = schema.get("items", {"type": "string"})
            return [self._generate_example_value(items_schema)]

        elif schema_type == "string":
            if "enum" in schema:
                return schema["enum"][0]
            if schema.get("format") == "date":
                return "2024-01-15"
            if schema.get("format") == "date-time":
                return "2024-01-15T10:00:00Z"
            return schema.get("description", "example")[:50]

        elif schema_type == "integer":
            return schema.get("minimum", 1)

        elif schema_type == "number":
            return schema.get("minimum", 0.0)

        elif schema_type == "boolean":
            return True

        return None

    def validate_schema(self, schema: Dict[str, Any]) -> ValidateSchemaResponse:
        """Validate JSON Schema for Gemini compatibility."""
        errors = []
        warnings = []

        # Check required top-level type
        if "type" not in schema:
            errors.append("Schema must have a 'type' field")

        # Validate type value
        valid_types = {"string", "number", "integer", "boolean", "object", "array", "null"}
        schema_type = schema.get("type")
        if schema_type and schema_type not in valid_types:
            errors.append(f"Invalid type '{schema_type}'. Must be one of: {valid_types}")

        # Check for descriptions (warning only)
        if schema_type == "object":
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if "description" not in prop_schema:
                    warnings.append(f"Property '{prop_name}' lacks description")

        # Validate nested structures
        self._validate_nested(schema, errors, warnings, path="root")

        return ValidateSchemaResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            supported_by_gemini=len(errors) == 0,
        )

    def _validate_nested(
        self,
        schema: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
        path: str,
    ) -> None:
        """Recursively validate nested schema structures."""
        schema_type = schema.get("type")

        if schema_type == "object":
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                self._validate_nested(
                    prop_schema,
                    errors,
                    warnings,
                    f"{path}.{prop_name}",
                )

        elif schema_type == "array":
            items = schema.get("items")
            if items:
                self._validate_nested(items, errors, warnings, f"{path}[]")
            else:
                warnings.append(f"Array at '{path}' lacks 'items' definition")

    def get_templates(self) -> SchemaTemplatesResponse:
        """Get all pre-built schema templates."""
        templates = []
        for template_id, schema in SCHEMA_TEMPLATES.items():
            templates.append(SchemaTemplateInfo(
                id=template_id,
                name=template_id.replace("_", " ").title(),
                description=f"Pre-built schema for {template_id.replace('_', ' ')}",
                domain="universal",
                schema=schema,
            ))
        return SchemaTemplatesResponse(templates=templates)

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific schema template."""
        return SCHEMA_TEMPLATES.get(template_id)
