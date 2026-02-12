#!/usr/bin/env python3
"""Script to migrate endpoints to use response wrapper and domain exceptions."""
import re
from pathlib import Path


def migrate_to_response_wrapper(file_path: Path) -> None:
    """Update file to use response wrapper."""
    content = file_path.read_text()
    
    # Add imports if not present
    if "from app.schemas.base import" not in content:
        imports_section = re.search(r'from app\.schemas import.*?\n', content)
        if imports_section:
            insert_pos = imports_section.end()
            content = content[:insert_pos] + f"from app.schemas.base import APIResponse, ResponseMeta\n" + content[insert_pos:]
    
    # Replace direct returns with APIResponse
    # Pattern: return response_object -> return APIResponse(data=response_object, meta=ResponseMeta(...))
    
    # Find all return statements and wrap them
    # This is a simplified approach - actual migration would need more context
    
    file_path.write_text(content)
    print(f"✓ Updated {file_path}")


def migrate_to_domain_exceptions(file_path: Path) -> None:
    """Update file to use domain exceptions."""
    content = file_path.read_text()
    
    # Add domain exceptions import if not present
    if "from app.core.exceptions import" not in content:
        imports_section = re.search(r'from.*?\n', content)
        if imports_section:
            insert_pos = imports_section.end()
            content = content[:insert_pos] + f"from app.core.exceptions import (\n    NotFoundError,\n    ValidationError,\n    BusinessRuleError,\n    AuthenticationError,\n    AuthorizationError,\n)\n" + content[insert_pos:]
    
    # Replace HTTPException with domain exceptions
    content = re.sub(
        r'raise HTTPException\(status_code=404, detail="([^"]+)"\)',
        r'raise NotFoundError("user", message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=404, detail="([^"]+)"\)',
        r'raise NotFoundError("program", message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=404, detail="([^"]+)"\)',
        r'raise NotFoundError("movement", message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=404, detail="([^"]+)"\)',
        r'raise NotFoundError("circuit", message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=400, detail="([^"]+)"\)',
        r'raise ValidationError("field", message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=409, detail="([^"]+)"\)',
        r'raise BusinessRuleError(message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=401, detail="([^"]+)"\)',
        r'raise AuthenticationError(message=\1)',
        content
    )
    
    content = re.sub(
        r'raise HTTPException\(status_code=403, detail="([^"]+)"\)',
        r'raise AuthorizationError(message=\1)',
        content
    )
    
    # Remove old HTTPException import if all replaced
    if '"from fastapi import' in content and 'HTTPException' in content:
        content = re.sub(
            r'from fastapi import ([^\\n]*?)HTTPException,?\\s*',
            r'from fastapi import \1',
            content
        )
    
    file_path.write_text(content)
    print(f"✓ Updated {file_path}")


def main() -> None:
    """Run migration on all route files."""
    routes_dir = Path(__file__).parent.parent / "app" / "api" / "routes"
    
    for route_file in routes_dir.glob("*.py"):
        if route_file.name.startswith("_"):
            continue
        
        print(f"Processing {route_file.name}...")
        migrate_to_response_wrapper(route_file)
        migrate_to_domain_exceptions(route_file)
    
    print(f"\n✓ Migration complete")


if __name__ == "__main__":
    main()
