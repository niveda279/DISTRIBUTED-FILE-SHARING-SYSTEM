"""Password hashing utilities."""
import sys

# ── passlib / bcrypt compatibility patch ──────────────────────────────────────
# passlib 1.7.4 accesses bcrypt.__about__.__version__ on import, but
# bcrypt ≥ 4.0 removed that module. Inject a stub so passlib initialises cleanly.
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        from types import ModuleType
        _about = ModuleType("bcrypt.__about__")
        _about.__version__ = bcrypt.__version__
        sys.modules.setdefault("bcrypt.__about__", _about)
        bcrypt.__about__ = _about  # type: ignore[attr-defined]
except Exception:
    pass
# ─────────────────────────────────────────────────────────────────────────────

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
