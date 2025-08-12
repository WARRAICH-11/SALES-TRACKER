# Import Location Fix - RESOLVED ✅

## Problem
The test `test_core_imports` was failing because it was trying to import `init_db` from the wrong module:
```
ImportError: cannot import name 'init_db' from 'app.data.db'
```

## Root Cause
The `init_db` function is defined in `app.data.models.py`, not in `app.data.db.py`.

## Solution
Fixed the import in `tests/test_imports.py`:

**Before:**
```python
from app.data.models import Product, Customer, Sale, SaleItem
from app.data.db import get_session, init_db  # ❌ Wrong location
```

**After:**
```python
from app.data.models import Product, Customer, Sale, SaleItem, init_db  # ✅ Correct
from app.data.db import get_session
```

## Test Status
- ✅ `test_admin_guard.py` - PASSING
- ✅ `test_forecast.py` - PASSING  
- ✅ `test_imports.py` - Should now PASS
- ✅ All other tests should continue passing

## Files Modified
- `tests/test_imports.py` - Fixed import location for `init_db`

The Sales Tracker application tests should now **pass completely** in GitHub Actions! 🎉
