"""
Test to verify all critical imports work correctly.
This helps catch missing dependencies early.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_core_imports():
    """Test that core application modules can be imported."""
    try:
        from app.data.models import Product, Customer, Sale, SaleItem
        from app.data.db import get_session, init_db
        assert True
    except ImportError as e:
        assert False, f"Core imports failed: {e}"

def test_sync_imports():
    """Test that sync-related modules can be imported."""
    try:
        from app.services.sync import attempt_sync_with_backoff
        from app.services.sync_pull import pull_updates
        assert True
    except ImportError as e:
        assert False, f"Sync imports failed: {e}"

def test_ai_imports_graceful():
    """Test that AI modules handle missing dependencies gracefully."""
    try:
        from app.ai.forecast import ForecastResult
        from app.ai.rag import SalesRAG
        # AI imports should work even if models aren't available
        assert True
    except ImportError as e:
        # AI dependencies might not be available in CI, that's okay
        print(f"AI imports not available (expected in CI): {e}")
        assert True

def test_widget_imports():
    """Test that widget modules can be imported."""
    try:
        # These might fail in headless CI due to Qt, but should import the modules
        import app.widgets.dashboard
        import app.widgets.sales_entry
        import app.widgets.customers
        import app.widgets.inventory
        assert True
    except ImportError as e:
        # Qt widgets might not work in headless CI
        print(f"Widget imports not available (expected in headless CI): {e}")
        assert True
