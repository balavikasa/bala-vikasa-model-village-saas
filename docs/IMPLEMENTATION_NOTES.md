# Implementation decisions and trade-offs

## Twelve tables, not eleven

The specification labels the schema as eleven tables but enumerates twelve distinct entities.
Dropping either audit logs or recycle-bin snapshots would remove required behavior, so all twelve are
implemented.

## Failure is a projection

“Failure” is the state of an overdue action plan with no attendance submission. It is calculated in
monitoring queries rather than inserted as a fabricated attendance row. This keeps the event table
truthful and allows a late submission to change the projected state naturally.

## Cluster normalization

Only `PC.cluster` is persisted. A DA move can therefore alter inherited cluster visibility for its
villages. The admin move API requires explicit acknowledgement and blocks moves that would make
historical submissions contradict their original hierarchy.

## Offline replay

Background Sync is opportunistic, not the sole delivery path. The PWA also retries on `online` and
window focus. IndexedDB records are partitioned by authenticated profile, carry client UUIDs, and
remain visible after permanent errors. Server idempotency is authoritative.

## Images

Browser compression saves bandwidth, but it is not a security boundary. The server decodes,
validates dimensions/size, applies EXIF orientation, strips metadata, and writes a newly encoded
WebP file with a generated name.

## Dash, Leaflet, and Three.js

The core field workflow does not depend on WebGL or dashboard libraries. Monitoring surfaces load
progressively. Dash is mounted inside the Flask process for the requested deployment shape; at larger
scale it can be moved behind the same identity-aware proxy without changing domain APIs.

## Upload storage

The included filesystem storage is appropriate for local development and a single durable container
volume. A horizontally scaled production deployment should replace it with an object-storage adapter
and signed or authenticated delivery; database records already store opaque generated references.

## Service-worker updates

Static caches are versioned. A newly activated worker removes prior application cache versions.
Queued submissions live in IndexedDB and are never evicted as part of a static cache upgrade.
