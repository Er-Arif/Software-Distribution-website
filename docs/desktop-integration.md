# Desktop App Integration Guide

Desktop apps must never trust local state as the final authority. They should trust only signed server responses verified with the embedded public key.

## Fingerprint Strategy

Send a versioned fingerprint payload:

```json
{
  "version": "v1",
  "machine_id": "stable-os-machine-id",
  "os": "windows",
  "os_version": "11",
  "app_installation_id": "generated-on-first-run",
  "cpu_hash": "optional",
  "motherboard_hash": "optional",
  "fallback_hash": "fallback-when-hardware-ids-unavailable"
}
```

The server stores the fingerprint hash, version, components, confidence score, and activation history. A small tolerance is allowed for legitimate hardware changes.

## Activation

`POST /api/v1/desktop/licenses/activate`

```json
{
  "license_key": "SW-ABCDE-FGHIJ-KLMNO-PQRST",
  "product_slug": "codevault-pro",
  "app_version": "1.0.0",
  "device_label": "Workstation",
  "fingerprint": {
    "version": "v1",
    "machine_id": "machine",
    "os": "windows",
    "app_installation_id": "install-id"
  }
}
```

## Signed Response Verification

The response contains:

- `payload`
- `signature`
- `algorithm`
- `public_key_id`

The app should:

1. Canonicalize the payload as JSON with sorted keys.
2. Verify the signature with the public key matching `public_key_id`.
3. Reject expired tokens using `exp`.
4. Reject repeated nonces if replay tracking is available.
5. Cache the payload only until `offline_valid_until`.

## Offline Rules

- Paid licenses default to 7 offline days.
- Trial licenses default to 3 offline days.
- Revoked, suspended, or blacklisted licenses block on next online validation and receive no new offline token.
- Expired licenses enter limited mode or block based on policy.
- The app should detect obvious clock rollback using monotonic timestamps and last-seen server time.

## Updates

Call `GET /api/v1/desktop/updates/manifest` with product, OS, architecture, and current version. The manifest is signed and may force an upgrade if the current app version is below the minimum supported version.
