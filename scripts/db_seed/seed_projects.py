#!/usr/bin/env python3
"""
Seed construction projects from Excel file.

Imports projects from 'список проектов.xls', filtering out codes longer than 4 digits.

Usage:
    python scripts/db_seed/seed_projects.py [--dry-run] [--tenant svrd]

Options:
    --dry-run   Preview without writing to database
    --tenant    Tenant slug (default: svrd)
    --file      Path to Excel file
"""
import asyncio
import sys
from pathlib import Path
import argparse
import importlib.util

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas is required. Install with: pip install pandas xlrd")
    sys.exit(1)

from sqlalchemy import select

from backend.shared.database import async_session_factory, init_db
from backend.shared.models import Tenant


def _load_construction_models():
    """Load construction models without importing heavy domain services."""
    module_path = PROJECT_ROOT / "backend" / "domains" / "construction" / "models.py"
    spec = importlib.util.spec_from_file_location("construction_models", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec and spec.loader:
        spec.loader.exec_module(module)
    return module


_construction_models = _load_construction_models()
ConstructionProject = _construction_models.ConstructionProject


def load_projects_from_excel(excel_path: str) -> list[dict]:
    """
    Load projects from Excel file.

    Returns list of dicts with 'code' and 'name' keys.
    Filters out codes > 4 digits.
    """
    df = pd.read_excel(excel_path)

    # Filter valid codes (1-4 digits only)
    df['code_str'] = df['Кодификатор'].astype(str)
    valid = df[df['code_str'].str.match(r'^\d{1,4}$')]

    # Drop rows with NaN names
    valid = valid.dropna(subset=['Наименование.1'])

    projects = []
    for _, row in valid.iterrows():
        code = str(int(row['Кодификатор'])).zfill(4)
        name = str(row['Наименование.1']).strip()
        projects.append({'code': code, 'name': name})

    return projects


async def ensure_tenant(db, tenant_slug: str) -> Tenant:
    """Get or create tenant."""
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()

    if not tenant:
        print(f"ERROR: Tenant '{tenant_slug}' not found!")
        print("Available tenants:")
        all_tenants = await db.execute(select(Tenant))
        for t in all_tenants.scalars():
            print(f"  - {t.slug}: {t.name}")
        return None

    return tenant


async def seed_projects(projects: list[dict], tenant_slug: str, dry_run: bool = False):
    """Seed projects to database."""
    print("\n" + "=" * 60)
    print("SEEDING PROJECTS FROM EXCEL")
    print("=" * 60)
    print(f"Tenant: {tenant_slug}")
    print(f"Projects to import: {len(projects)}")
    print(f"Dry run: {dry_run}")
    print("=" * 60 + "\n")

    if dry_run:
        print("DRY RUN - No changes will be made\n")
        for p in projects[:10]:
            print(f"  [{p['code']}] {p['name']}")
        if len(projects) > 10:
            print(f"  ... and {len(projects) - 10} more")
        print("\nRun without --dry-run to apply changes.")
        return

    await init_db()

    created = 0
    updated = 0
    skipped = 0

    async with async_session_factory() as db:
        tenant = await ensure_tenant(db, tenant_slug)
        if not tenant:
            return

        for project_data in projects:
            code = project_data['code']
            name = project_data['name']

            # Check if project with this code already exists
            result = await db.execute(
                select(ConstructionProject).where(
                    ConstructionProject.project_code == code
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update name if different
                if existing.name != name:
                    old_name = existing.name
                    existing.name = name
                    existing.tenant_id = tenant.id
                    updated += 1
                    print(f"[UPD] {code}: '{old_name}' -> '{name}'")
                else:
                    skipped += 1
            else:
                # Create new project
                project = ConstructionProject(
                    name=name,
                    project_code=code,
                    tenant_id=tenant.id,
                    is_active=True,
                )
                db.add(project)
                created += 1
                print(f"[NEW] {code}: {name}")

        await db.commit()

    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Skipped (no changes): {skipped}")
    print(f"Total: {len(projects)}")


def main():
    parser = argparse.ArgumentParser(description="Seed projects from Excel file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing to database"
    )
    parser.add_argument(
        "--tenant",
        default="svrd",
        help="Tenant slug (default: svrd)"
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Path to Excel file (default: deploy/data/projects.xls)"
    )

    args = parser.parse_args()

    # Default file location
    if args.file:
        excel_path = Path(args.file)
    else:
        excel_path = PROJECT_ROOT / "deploy" / "data" / "projects.xls"

    if not excel_path.exists():
        # Try alternative location
        alt_path = PROJECT_ROOT / "список проектов.xls"
        if alt_path.exists():
            excel_path = alt_path
        else:
            print(f"ERROR: File not found: {excel_path}")
            print(f"       Also tried: {alt_path}")
            sys.exit(1)

    print(f"Loading projects from: {excel_path}")
    projects = load_projects_from_excel(str(excel_path))
    print(f"Found {len(projects)} valid projects (codes 1-4 digits)")

    asyncio.run(seed_projects(projects, args.tenant, args.dry_run))


if __name__ == "__main__":
    main()
