"""
Domain Service Factory.

Provides factory pattern for creating domain-specific services
based on domain type. Service classes загружаются лениво из единого
реестра (registry.py).
"""
import logging
import importlib
from typing import Dict, Type, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseDomainService

logger = logging.getLogger(__name__)


class DomainServiceFactory:
    """
    Factory for creating domain-specific services.

    Registers domain services and creates instances based on domain_type.
    Service paths are defined in registry.py; lazy-loaded on first use.

    Usage:
        factory = DomainServiceFactory()
        service = factory.create('construction', db, gemini_client=client)
        report = await service.generate_report(result, project_id)
    """

    _registry: Dict[str, Type[BaseDomainService]] = {}

    @classmethod
    def register(cls, domain_type: str, service_class: Type[BaseDomainService]) -> None:
        """Register a domain service class."""
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

        Lazy-loads the service class from registry on first access.
        """
        # Lazy-load if not yet registered
        if domain_type not in cls._registry:
            cls._load_from_registry(domain_type)

        service_class = cls._registry.get(domain_type)
        if not service_class:
            raise ValueError(f"Unknown domain type: '{domain_type}'")

        if db is not None:
            kwargs['db'] = db
        return service_class(**kwargs)

    @classmethod
    def get_available_domains(cls) -> list[str]:
        """Get list of all domain types from registry."""
        from .registry import get_all_domain_ids
        return get_all_domain_ids()

    @classmethod
    def is_registered(cls, domain_type: str) -> bool:
        """Check if domain type is registered."""
        if domain_type in cls._registry:
            return True
        from .registry import DOMAINS
        return domain_type in DOMAINS

    @classmethod
    def _load_from_registry(cls, domain_type: str) -> None:
        """Load service class from registry's service_path."""
        from .registry import DOMAINS
        defn = DOMAINS.get(domain_type)
        if not defn or not defn.service_path:
            return

        try:
            module_path, class_name = defn.service_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            service_class = getattr(module, class_name)
            cls._registry[domain_type] = service_class
            logger.debug(f"Loaded domain service: {domain_type} -> {defn.service_path}")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Domain {domain_type} service not available: {e}")
