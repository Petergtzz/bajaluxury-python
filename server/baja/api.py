from fastapi import APIRouter

from baja.auth.endpoints import router as auth_router
from baja.guest_expense.endpoints import router as guest_expense_router
from baja.ledger.endpoints import router as ledger_router
from baja.login_code.endpoints import router as login_code_router
from baja.property.endpoints import router as property_router
from baja.shortcut.endpoints import router as shortcut_router
from baja.user.endpoints import router as user_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(guest_expense_router)
router.include_router(ledger_router)
router.include_router(login_code_router)
router.include_router(property_router)
router.include_router(shortcut_router)
router.include_router(user_router)
