"""
Prompt templates and AI schema generation router.

Endpoints for:
- CRUD operations on prompt templates
- AI-powered JSON Schema generation
- Schema validation
- Pre-built schema templates
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.core.auth.dependencies import SuperUser
from .service import PromptService, SchemaGeneratorService
from .schemas import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
    GenerateSchemaRequest,
    GeneratedSchemaResponse,
    ValidateSchemaRequest,
    ValidateSchemaResponse,
    SchemaTemplatesResponse,
    SCHEMA_TEMPLATES,
)


router = APIRouter(prefix="/prompts", tags=["Admin - Prompts & Schemas"])


# =============================================================================
# Prompt Template CRUD
# =============================================================================

@router.get(
    "/templates",
    response_model=PromptTemplateListResponse,
    summary="List prompt templates",
    description="Get all prompt templates with optional filtering by domain."
)
async def list_templates(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    domain: Optional[str] = Query(None, description="Filter by domain"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> PromptTemplateListResponse:
    """List all prompt templates."""
    service = PromptService(db)
    return await service.list_templates(
        domain=domain,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Get prompt template by ID",
)
async def get_template(
    template_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptTemplateResponse:
    """Get a specific prompt template."""
    service = PromptService(db)
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    return PromptTemplateResponse.model_validate(template)


@router.get(
    "/templates/slug/{slug}",
    response_model=PromptTemplateResponse,
    summary="Get prompt template by slug",
)
async def get_template_by_slug(
    slug: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptTemplateResponse:
    """Get a prompt template by its slug."""
    service = PromptService(db)
    template = await service.get_template_by_slug(slug)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with slug '{slug}' not found"
        )
    return PromptTemplateResponse.model_validate(template)


@router.post(
    "/templates",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create prompt template",
    description="Create a new prompt template with optional JSON Schema."
)
async def create_template(
    data: PromptTemplateCreate,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptTemplateResponse:
    """Create a new prompt template."""
    service = PromptService(db)
    try:
        template = await service.create_template(
            data,
            created_by=current_user.email,
        )
        return PromptTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch(
    "/templates/{template_id}",
    response_model=PromptTemplateResponse,
    summary="Update prompt template",
)
async def update_template(
    template_id: int,
    data: PromptTemplateUpdate,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PromptTemplateResponse:
    """Update a prompt template."""
    service = PromptService(db)
    template = await service.update_template(template_id, data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )
    return PromptTemplateResponse.model_validate(template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete prompt template",
)
async def delete_template(
    template_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a prompt template."""
    service = PromptService(db)
    deleted = await service.delete_template(template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )


# =============================================================================
# AI Schema Generator
# =============================================================================

@router.post(
    "/generate-schema",
    response_model=GeneratedSchemaResponse,
    summary="Generate JSON Schema from description",
    description="""
Use AI to generate a JSON Schema from natural language description.

**Example request:**
```json
{
    "description": "I need a report with list of tasks, each having title,
                    responsible person, deadline, and priority (high/medium/low)",
    "output_type": "report",
    "include_metadata": true
}
```

The AI will analyze the description and generate a Gemini-compatible JSON Schema.
"""
)
async def generate_schema(
    request: GenerateSchemaRequest,
    current_user: SuperUser,
) -> GeneratedSchemaResponse:
    """
    Generate JSON Schema from natural language description.

    Uses Gemini AI to interpret the description and produce
    a valid JSON Schema compatible with Gemini structured output.
    """
    service = SchemaGeneratorService()
    try:
        return await service.generate_schema(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema generation failed: {str(e)}"
        )


@router.post(
    "/validate-schema",
    response_model=ValidateSchemaResponse,
    summary="Validate JSON Schema for Gemini compatibility",
    description="Check if a JSON Schema is compatible with Gemini structured output."
)
async def validate_schema(
    request: ValidateSchemaRequest,
    current_user: SuperUser,
) -> ValidateSchemaResponse:
    """Validate a JSON Schema for Gemini compatibility."""
    service = SchemaGeneratorService()
    return service.validate_schema(request.schema)


# =============================================================================
# Pre-built Schema Templates
# =============================================================================

@router.get(
    "/schema-templates",
    response_model=SchemaTemplatesResponse,
    summary="List pre-built schema templates",
    description="Get all available pre-built schema templates."
)
async def list_schema_templates(
    current_user: SuperUser,
) -> SchemaTemplatesResponse:
    """List all pre-built schema templates."""
    service = SchemaGeneratorService()
    return service.get_templates()


@router.get(
    "/schema-templates/{template_id}",
    summary="Get pre-built schema template",
    description="Get a specific pre-built schema template."
)
async def get_schema_template(
    template_id: str,
    current_user: SuperUser,
) -> dict:
    """Get a specific pre-built schema template."""
    service = SchemaGeneratorService()
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema template '{template_id}' not found. "
                   f"Available: {list(SCHEMA_TEMPLATES.keys())}"
        )
    return {
        "id": template_id,
        "schema": template,
    }


# =============================================================================
# Domains List
# =============================================================================

@router.get(
    "/domains",
    summary="List available domains",
    description="Get list of available domains for prompt templates."
)
async def list_domains(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List all domains with template counts."""
    from sqlalchemy import func, select
    from backend.admin.models import PromptTemplate

    result = await db.execute(
        select(
            PromptTemplate.domain,
            func.count(PromptTemplate.id).label("count")
        )
        .group_by(PromptTemplate.domain)
    )

    domains = {row[0]: row[1] for row in result.all()}

    # Add standard domains if not present
    standard_domains = ["construction", "hr", "universal"]
    for d in standard_domains:
        if d not in domains:
            domains[d] = 0

    return {
        "domains": [
            {"name": name, "template_count": count}
            for name, count in sorted(domains.items())
        ]
    }
