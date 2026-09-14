def health_status(ok: bool, critical: bool = False) -> str:
    if ok:
        return "OK"
    return "CRITICAL" if critical else "DEGRADED"
