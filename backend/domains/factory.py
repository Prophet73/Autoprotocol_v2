"""
Domain Service Factory.

Provides factory pattern for creating domain-specific services
based on domain type. Used by transcription pipeline to route
to correct domain logic after transcription completes.
"""
from typing import Dict, Type, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseDomainService


class DomainServiceFactory:
    """
    Factory for creating domain-specific services.

    Registers domain services and creates instances based on domain_type.
    Used by Celery tasks to route transcription results to correct domain logic.

    Usage:
        factory = DomainServiceFactory()
        service = factory.create('construction', db, gemini_client=client)
        report = await service.generate_report(result, project_id)
    """

    _registry: Dict[str, Type[BaseDomainService]] = {}

    @classmethod
    def register(cls, domain_type: str, service_class: Type[BaseDomainService]) -> None:
        """
        Register a domain service class.

        Args:
            domain_type: Domain identifier (e.g., 'construction', 'hr')
            service_class: Service class that extends BaseDomainService
        """
        cls._registry[domain_type] = service_class

    @classmethod
    def create(
        cls,
        domain_type: str,
        db: Optional[AsyncSession] = None,
        **kwargs: Any
    ) -> BaseDomainService:
        """
        Create a domain service instance.

        Args:
            domain_type: Domain identifier
            db: Database session (optional, passed to service)
            **kwargs: Additional arguments for service constructor

        Returns:
            Instance of domain service

        Raises:
            ValueError: If domain_type is not registered
        """
        service_class = cls._registry.get(domain_type)

        if not service_class:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Unknown domain type: '{domain_type}'. "
                f"Available domains: {available}"
            )

        # Pass db as llm_client placeholder if using new pattern
        # Most domains will use kwargs for gemini_client etc.
        return service_class(**kwargs)

    @classmethod
    def get_available_domains(cls) -> list[str]:
        """Get list of registered domain types."""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, domain_type: str) -> bool:
        """Check if domain type is registered."""
        return domain_type in cls._registry


# Auto-register construction domain on import
def _register_default_domains():
    """Register built-in domain services."""
    try:
        from .construction.service import ConstructionService
        DomainServiceFactory.register('construction', ConstructionService)
    except ImportError:
        pass  # Construction domain not available


# Register on module load
_register_default_domains()
