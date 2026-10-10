> **Final — version 2026-10, effective 2026-10-10 (Ontario ESA Part XI.1).** Shown to drivers in the driver app/portal (onboarding acknowledgment with timestamp + version, settings, GPS consent prompt) and in admin Settings → Compliance. The in-app text is served from `apps/api/src/porterchain_api/platform/monitoring_policy.py`; keep both in sync and bump `POLICY_VERSION` on any change (drivers re-acknowledge; give the changed policy to employees within 30 days).

# Electronic Monitoring Policy — PorterChain Logistics Inc.

**Date prepared:** 2026-10-10 · **Last changed:** 2026-10-10 · **Version:** 2026-10

## Does PorterChain monitor workers electronically?

Yes. This is how, when and why.

| Monitoring               | How                                                              | When                                                  | Why                                                                 |
| ------------------------ | ---------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------- |
| Driver location (GPS)    | Driver app or portal on the driver's phone sends location        | Only while the driver is on shift                     | Dispatch, routing, safety, customer arrival times, proof of service |
| Road-matched route trail | Our servers snap GPS points to roads (self-hosted Valhalla/OSRM) | On shift; viewable by dispatch for the last few hours | Accurate arrival times, investigating delivery issues               |
| Proof of delivery        | Photo, signature, timestamps and location at each stop           | At each delivery                                      | Prove delivery, handle claims                                       |
| Delivery app events      | Arrive, deliver and fail actions with timestamps                 | On shift                                              | Arrival times, pay, service quality                                 |
| Staff admin systems      | Sign-in records and audit logs of settings changes               | When staff use admin tools                            | Security, accountability                                            |

## Controls

- Location is never collected off shift.
- PorterChain can turn live location off for all drivers or for one driver. When it is off, the app stops sending location, and the live position is deleted immediately.
- Drivers are asked to agree in the app before location is collected. A driver who withdraws consent is not tracked.
- Customers see only the arrival time and stop status, never a driver's location history.
- Location history is deleted after 30 days. Proof-of-delivery records are kept for 365 days.

## How information may be used

Monitoring information may be used to plan and assign work, calculate pay and mileage, investigate complaints, claims or safety incidents, and meet legal obligations. It is not used for any other purpose.

## Questions

Contact Ravi Chauhan, Owner (accountable for privacy), privacy@porterchain.com or sales@porterchain.com.
