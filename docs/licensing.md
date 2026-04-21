# Licensing

Licensing is intentionally not tightly coupled to payment plans.

## Core Tables

- `license_policies`: offline days, grace days, update access window, max devices, revalidation interval.
- `activation_rules`: fingerprint version, tolerance, reset limits, abuse thresholds.
- `entitlements`: feature access by product, plan, license, or user.
- `feature_flags`: global, product, plan, license, or user-scoped feature switches.
- `licenses`: actual customer/admin-granted license record.
- `devices` and `license_activations`: device binding and activation history.

## License Types

- Lifetime
- Subscription
- Trial
- Manual admin-created
- Offline enterprise
- Custom grant without payment

## Abuse Detection

Suspicious state is raised for:

- Too many activations in a short window.
- Frequent device switching.
- Repeated failed validations.
- Repeated bad license keys.
- Abnormal download behavior.

Suspicious accounts are surfaced to admins and recorded as domain events.
