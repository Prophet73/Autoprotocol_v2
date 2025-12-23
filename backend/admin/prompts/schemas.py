"""
Schemas for prompt template management and AI schema generation.

Based on Gemini API structured output capabilities:
- Supported types: string, number, integer, boolean, object, array, null
- Descriptive properties: title, description, enum, format, minimum/maximum
- Array constraints: items, minItems, maxItems
- Object constraints: properties, required
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# =============================================================================
# JSON Schema Types (Gemini-compatible)
# =============================================================================

class JsonSchemaType(str, Enum):
    """Supported JSON Schema types for Gemini structured output."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


class JsonSchemaFormat(str, Enum):
    """Common format specifications for string types."""
    DATE = "date"
    DATE_TIME = "date-time"
    TIME = "time"
    EMAIL = "email"
    URI = "uri"
    UUID = "uuid"


# =============================================================================
# Prompt Template Schemas
# =============================================================================

class PromptTemplateBase(BaseModel):
    """Base fields for prompt template."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_-]+$")
    domain: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class PromptTemplateCreate(PromptTemplateBase):
    """Request to create a new prompt template."""
    system_prompt: str = Field(..., min_length=1)
    user_prompt_template: str = Field(..., min_length=1)
    response_schema: Optional[Dict[str, Any]] = None
    is_default: bool = False


class PromptTemplateUpdate(BaseModel):
    """Request to update a prompt template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    response_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class PromptTemplateResponse(PromptTemplateBase):
    """Prompt template response with all fields."""
    id: int
    system_prompt: str
    user_prompt_template: str
    response_schema: Optional[Dict[str, Any]]
    is_active: bool
    is_default: bool
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True


class PromptTemplateListResponse(BaseModel):
    """List of prompt templates."""
    templates: List[PromptTemplateResponse]
    total: int


# =============================================================================
# AI Schema Generator Schemas
# =============================================================================

class SchemaPropertyRequest(BaseModel):
    """Single property description for schema generation."""
    name: str = Field(..., description="Property name (snake_case)")
    description: str = Field(..., description="What this property represents")
    type_hint: Optional[str] = Field(None, description="Hint: string, number, array, etc.")
    required: bool = Field(True, description="Is this property required?")
    enum_values: Optional[List[str]] = Field(None, description="If enum, list of values")


class GenerateSchemaRequest(BaseModel):
    """
    Request to generate JSON Schema from natural language description.

    Example:
    {
        "description": "I need a report with list of tasks, each having title,
                        responsible person, deadline, and priority (high/medium/low)",
        "output_type": "report",
        "include_metadata": true
    }
    """
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language description of the desired output structure"
    )
    output_type: Optional[str] = Field(
        "report",
        description="Type hint: report, analysis, tasks, summary, etc."
    )
    include_metadata: bool = Field(
        True,
        description="Include standard metadata fields (title, date, author)"
    )
    language: str = Field(
        "ru",
        description="Target language for field descriptions"
    )
    properties: Optional[List[SchemaPropertyRequest]] = Field(
        None,
        description="Optional explicit property definitions to include"
    )


class GeneratedSchemaResponse(BaseModel):
    """Response with generated JSON Schema."""
    schema: Dict[str, Any] = Field(..., description="Generated JSON Schema")
    schema_name: str = Field(..., description="Suggested schema name")
    description: str = Field(..., description="Schema description")
    example_output: Optional[Dict[str, Any]] = Field(
        None,
        description="Example of what the output would look like"
    )
    validation_status: str = Field("valid", description="Schema validation status")
    gemini_model: str = Field(..., description="Model used for generation")


class ValidateSchemaRequest(BaseModel):
    """Request to validate a JSON Schema."""
    schema: Dict[str, Any] = Field(..., description="JSON Schema to validate")


class ValidateSchemaResponse(BaseModel):
    """Schema validation response."""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    supported_by_gemini: bool = True


# =============================================================================
# Schema Templates (pre-built schemas for common use cases)
# =============================================================================

class SchemaTemplateInfo(BaseModel):
    """Information about a pre-built schema template."""
    id: str
    name: str
    description: str
    domain: str
    schema: Dict[str, Any]


class SchemaTemplatesResponse(BaseModel):
    """List of available schema templates."""
    templates: List[SchemaTemplateInfo]


# =============================================================================
# Gemini Structured Output Configuration
# =============================================================================

# Pre-defined JSON Schemas for common report types
SCHEMA_TEMPLATES = {
    "basic_report": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Report title"
            },
            "summary": {
                "type": "string",
                "description": "Executive summary"
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["heading", "content"]
                }
            },
            "conclusions": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["title", "summary"]
    },

    "task_list": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Task description"
                        },
                        "responsible": {
                            "type": "string",
                            "description": "Person responsible"
                        },
                        "deadline": {
                            "type": "string",
                            "format": "date",
                            "description": "Due date"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Task priority"
                        },
                        "category": {
                            "type": "string",
                            "description": "Task category"
                        }
                    },
                    "required": ["description", "responsible"]
                }
            },
            "total_count": {
                "type": "integer",
                "description": "Total number of tasks"
            }
        },
        "required": ["tasks"]
    },

    "risk_assessment": {
        "type": "object",
        "properties": {
            "overall_status": {
                "type": "string",
                "enum": ["stable", "attention", "critical"],
                "description": "Overall risk level"
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "probability": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        },
                        "impact": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        },
                        "mitigation": {"type": "string"},
                        "responsible": {"type": "string"}
                    },
                    "required": ["description", "probability", "impact"]
                }
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["overall_status", "risks"]
    },

    "meeting_protocol": {
        "type": "object",
        "properties": {
            "meeting_type": {
                "type": "string",
                "description": "Type of meeting"
            },
            "date": {
                "type": "string",
                "format": "date"
            },
            "participants": {
                "type": "array",
                "items": {"type": "string"}
            },
            "agenda": {
                "type": "array",
                "items": {"type": "string"}
            },
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string"},
                        "responsible": {"type": "string"},
                        "deadline": {"type": "string"}
                    },
                    "required": ["decision"]
                }
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "assignee": {"type": "string"},
                        "due_date": {"type": "string"}
                    },
                    "required": ["task"]
                }
            },
            "next_meeting": {
                "type": "string",
                "description": "Date/time of next meeting"
            }
        },
        "required": ["meeting_type", "decisions"]
    },

    "analysis_report": {
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": "Brief overview for executives"
            },
            "indicators": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["ok", "warning", "critical"]
                        },
                        "value": {"type": "string"},
                        "trend": {
                            "type": "string",
                            "enum": ["up", "down", "stable"]
                        },
                        "comment": {"type": "string"}
                    },
                    "required": ["name", "status"]
                }
            },
            "challenges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "problem": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "responsible": {"type": "string"}
                    },
                    "required": ["problem"]
                }
            },
            "achievements": {
                "type": "array",
                "items": {"type": "string"}
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["executive_summary", "indicators"]
    }
}
