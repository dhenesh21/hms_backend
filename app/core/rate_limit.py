from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance. Lives here (not in main.py) so individual
# routers can import it to apply per-endpoint limits (e.g. a stricter
# limit on login for brute-force protection) without main.py and the
# router importing each other.
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
