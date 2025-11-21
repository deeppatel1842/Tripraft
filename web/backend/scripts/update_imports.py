"""
Script to update imports after restructuring expense_engine
"""
import os
import re
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Import mapping: old -> new
IMPORT_MAPPINGS = {
    'from expense_engine.models.models import': 'from expense_engine.models.models import',
    'from expense_engine.models.enums import': 'from expense_engine.models.enums import',
    'from expense_engine.models.validators import': 'from expense_engine.models.validators import',
    'from expense_engine.models.decimal_utils import': 'from expense_engine.models.decimal_utils import',
    
    'from expense_engine.config.constants import': 'from expense_engine.config.constants import',
    'from expense_engine.config.production_config import': 'from expense_engine.config.production_config import',
    'from expense_engine.config.messages import': 'from expense_engine.config.messages import',
    
    'from expense_engine.core.service import': 'from expense_engine.core.service import',
    'from expense_engine.core.balance_manager import': 'from expense_engine.core.balance_manager import',
    
    'from expense_engine.services.firebase_operations import': 'from expense_engine.services.firebase_operations import',
    'from expense_engine.services.cache_operations import': 'from expense_engine.services.cache_operations import',
    'from expense_engine.services.email_service import': 'from expense_engine.services.email_service import',
    'from expense_engine.services.email_service_hybrid import': 'from expense_engine.services.email_service_hybrid import',
    'from expense_engine.services.local_storage import': 'from expense_engine.services.local_storage import',
    
    'from expense_engine.utils.logging_utils import': 'from expense_engine.utils.logging_utils import',
    'from expense_engine.utils.pagination import': 'from expense_engine.utils.pagination import',
    'from expense_engine.utils.rate_limiter import': 'from expense_engine.utils.rate_limiter import',
    'from expense_engine.utils.idempotency import': 'from expense_engine.utils.idempotency import',
    'from expense_engine.utils.firestore_counter import': 'from expense_engine.utils.firestore_counter import',
    
    # Relative imports within expense_engine
    'from .models.models import': 'from .models.models import',
    'from .models.enums import': 'from .models.enums import',
    'from .models.validators import': 'from .models.validators import',
    'from .models.decimal_utils import': 'from .models.decimal_utils import',
    
    'from .config.constants import': 'from .config.constants import',
    'from .config.production_config import': 'from .config.production_config import',
    'from .config.messages import': 'from .config.messages import',
    
    'from .core.service import': 'from .core.service import',
    'from .core.balance_manager import': 'from .core.balance_manager import',
    
    'from .services.firebase_operations import': 'from .services.firebase_operations import',
    'from .services.cache_operations import': 'from .services.cache_operations import',
    'from .services.email_service import': 'from .services.email_service import',
    'from .services.email_service_hybrid import': 'from .services.email_service_hybrid import',
    'from .services.local_storage import': 'from .services.local_storage import',
    
    'from .utils.logging_utils import': 'from .utils.logging_utils import',
    'from .utils.pagination import': 'from .utils.pagination import',
    'from .utils.rate_limiter import': 'from .utils.rate_limiter import',
    'from .utils.idempotency import': 'from .utils.idempotency import',
    'from .utils.firestore_counter import': 'from .utils.firestore_counter import',
}

def update_file_imports(filepath):
    """Update imports in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading: {e}"
    
    original_content = content
    changes = []
    
    for old_import, new_import in IMPORT_MAPPINGS.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            changes.append(f"  {old_import} -> {new_import}")
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes
    
    return False, []

def main():
    print("=" * 80)
    print("UPDATING IMPORTS AFTER RESTRUCTURE")
    print("=" * 80)
    print()
    
    # Directories to process
    dirs_to_process = [
        BASE_DIR / "expense_engine",
        BASE_DIR / "api",
        BASE_DIR / "Group_planner",
        BASE_DIR / "services",
        BASE_DIR / "scripts",
    ]
    
    total_files = 0
    total_changed = 0
    
    for directory in dirs_to_process:
        if not directory.exists():
            continue
            
        for filepath in directory.rglob("*.py"):
            # Skip backup files and pycache
            if '_backup_' in str(filepath) or '__pycache__' in str(filepath):
                continue
                
            changed, result = update_file_imports(filepath)
            
            if changed:
                total_changed += 1
                rel_path = filepath.relative_to(BASE_DIR)
                print(f"✓ {rel_path}")
                for change in result[:3]:  # Show first 3 changes
                    print(change)
                if len(result) > 3:
                    print(f"  ... and {len(result) - 3} more")
                print()
            
            total_files += 1
    
    print("=" * 80)
    print(f"Processed {total_files} files")
    print(f"Modified {total_changed} files")
    print("=" * 80)

if __name__ == "__main__":
    main()
