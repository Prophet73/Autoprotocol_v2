#!/usr/bin/env python3
"""
Debug script to check project managers for critical notification.

Usage:
    python scripts/debug_project_managers.py 7777
    
Or for project by ID:
    python scripts/debug_project_managers.py --id 123
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def check_project_managers(project_code: str = None, project_id: int = None):
    """Check project managers and their roles."""
    from backend.shared.database import async_session_factory
    from backend.domains.construction.models import ConstructionProject
    from backend.core.email.service import RISK_BRIEF_ALLOWED_ROLES
    
    async with async_session_factory() as db:
        query = select(ConstructionProject).options(
            selectinload(ConstructionProject.manager),
            selectinload(ConstructionProject.managers)
        )
        
        if project_code:
            query = query.where(ConstructionProject.project_code == project_code)
        elif project_id:
            query = query.where(ConstructionProject.id == project_id)
        else:
            print("ERROR: Specify either project_code or --id project_id")
            return
        
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            print(f"ERROR: Project not found (code={project_code}, id={project_id})")
            return
        
        print(f"\n{'='*60}")
        print(f"PROJECT INFO")
        print(f"{'='*60}")
        print(f"ID:          {project.id}")
        print(f"Name:        {project.name}")
        print(f"Code:        {project.project_code}")
        print(f"Manager ID:  {project.manager_id}")
        print(f"Tenant ID:   {project.tenant_id}")
        print(f"Is Active:   {project.is_active}")
        
        print(f"\n{'='*60}")
        print(f"MAIN MANAGER (manager_id -> User)")
        print(f"{'='*60}")
        
        manager_emails = []
        
        if project.manager:
            mgr = project.manager
            print(f"ID:          {mgr.id}")
            print(f"Email:       {mgr.email}")
            print(f"Name:        {mgr.name}")
            print(f"Role:        {mgr.role}")
            print(f"Is Active:   {mgr.is_active}")
            
            if mgr.is_active:
                if mgr.role in RISK_BRIEF_ALLOWED_ROLES:
                    print(f"✅ Would receive notification: role {mgr.role} is in {RISK_BRIEF_ALLOWED_ROLES}")
                    manager_emails.append(mgr.email)
                else:
                    print(f"❌ Would NOT receive notification: role {mgr.role} not in {RISK_BRIEF_ALLOWED_ROLES}")
            else:
                print(f"❌ Would NOT receive notification: user is not active")
        else:
            print("No main manager assigned (manager_id is NULL or user deleted)")
        
        print(f"\n{'='*60}")
        print(f"M2M MANAGERS (project_managers table)")
        print(f"{'='*60}")
        
        if project.managers:
            for i, mgr in enumerate(project.managers, 1):
                print(f"\n--- Manager #{i} ---")
                print(f"ID:          {mgr.id}")
                print(f"Email:       {mgr.email}")
                print(f"Name:        {mgr.name}")
                print(f"Role:        {mgr.role}")
                print(f"Is Active:   {mgr.is_active}")
                
                if mgr.is_active:
                    if mgr.role in RISK_BRIEF_ALLOWED_ROLES:
                        if mgr.email not in manager_emails:
                            print(f"✅ Would receive notification: role {mgr.role} is in {RISK_BRIEF_ALLOWED_ROLES}")
                            manager_emails.append(mgr.email)
                        else:
                            print(f"⚠️ Already added from main manager")
                    else:
                        print(f"❌ Would NOT receive notification: role {mgr.role} not in {RISK_BRIEF_ALLOWED_ROLES}")
                else:
                    print(f"❌ Would NOT receive notification: user is not active")
        else:
            print("No M2M managers (project_managers table is empty for this project)")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Allowed roles for notifications: {RISK_BRIEF_ALLOWED_ROLES}")
        print(f"Emails that would receive notification: {manager_emails}")
        
        if manager_emails:
            print(f"\n✅ {len(manager_emails)} manager(s) would be notified")
        else:
            print(f"\n❌ NO managers would be notified!")
            print("   Possible reasons:")
            print("   - No manager assigned to project")
            print("   - Manager(s) not active")
            print("   - Manager role not in allowed roles (manager, admin, superuser)")


async def check_job(job_id: str):
    """Check job info from database."""
    from backend.shared.database import async_session_factory
    from backend.shared.models import TranscriptionJob
    
    async with async_session_factory() as db:
        result = await db.execute(
            select(TranscriptionJob).where(TranscriptionJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            print(f"ERROR: Job {job_id} not found in database")
            return
        
        print(f"\n{'='*60}")
        print(f"JOB INFO")
        print(f"{'='*60}")
        print(f"Job ID:      {job.job_id}")
        print(f"Project ID:  {job.project_id}")
        print(f"Domain:      {job.domain}")
        print(f"Status:      {job.status}")
        print(f"User ID:     {job.user_id}")
        print(f"Guest UID:   {job.guest_uid}")
        print(f"Created:     {job.created_at}")
        print(f"Completed:   {job.completed_at}")
        
        if job.project_id:
            print(f"\n--> Checking project {job.project_id}...")
            await check_project_managers(project_id=job.project_id)
        else:
            print(f"\n❌ project_id is NULL! Critical notification cannot be sent!")


def main():
    parser = argparse.ArgumentParser(description="Debug project managers for critical notification")
    parser.add_argument("code", nargs="?", help="4-digit project code (e.g., 7777)")
    parser.add_argument("--id", type=int, help="Project ID instead of code")
    parser.add_argument("--job", help="Job ID to check")
    
    args = parser.parse_args()
    
    if args.job:
        asyncio.run(check_job(args.job))
    elif args.code or args.id:
        asyncio.run(check_project_managers(
            project_code=args.code,
            project_id=args.id
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
