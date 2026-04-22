from app.core.config import settings


DANGEROUS_MARKERS = (b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", b"<script", b"malware")


def scan_installer_bytes(data: bytes) -> tuple[str, str]:
    if any(marker.lower() in data.lower() for marker in DANGEROUS_MARKERS):
        return "blocked", "Matched local malware test marker"
    if settings.malware_scan_mode == "strict":
        return "pending", "Awaiting external malware scanner verdict"
    if settings.malware_scan_mode == "manual":
        return "pending", "Manual security review required"
    return "clean", "Local development scan passed"
