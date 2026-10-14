# agent-operation-ledger

Two agent workers should not both send the same action. An uncertain outcome should not silently become permission to try again.

This local SQLite ledger lets one controller reserve an operation key, record success or uncertainty, and block subsequent claims. Python 3.10+, standard library only. MIT. It never executes the operation.

## Try it

```sh
python3 -m unittest -v
python3 demo.py
```

14 synthetic tests include 16 concurrent claim attempts, restart persistence, changed payload conflicts, wrong owner tokens and uncertain outcomes. No network or account access.

## Controller contract

```python
from ledger import connect, claim, finish, payload_digest

db = connect('operations.db')
proposal = {'operation': 'synthetic-example', 'payload': 'not a real action'}
result = claim(db, 'your-stable-operation-key', payload_digest(proposal))
if result['status'] == 'claimed':
    # A separate trusted controller would perform the already-authorized operation.
    # If a request timed out or the controller cannot prove the outcome, use uncertain.
    finish(db, 'your-stable-operation-key', result['token'], 'uncertain')
db.close()
```

`claim` uses an immediate SQLite transaction and a unique operation key. Only the winning claim receives a random owner token. Repeating the same key/digest returns `already-recorded`; a changed digest returns `conflict`. Neither grants execution permission.

`finish` requires the owner token and changes `reserved` to `succeeded` or `uncertain` once. There is intentionally no automatic expiry, reset or retry. A controller crash leaves the reservation blocked for investigation. `status` returns metadata without the owner token.

CLI commands are also available:

```sh
python3 ledger.py --db operations.db status example-key
```

For `claim`, pass the stable key and digest. For `finish`, pass key and outcome and pipe the controller-owned claim token through stdin. Do not paste tokens into shell history or logs.

## Limits

- Not exactly-once external delivery. SQLite cannot atomically commit with a remote service. A crash between remote success and local completion remains uncertain. Prefer vendor idempotency keys too.
- Not a permission gate, authentication system or approval UI. This complements action-boundary rather than replacing it.
- Stable keys are the caller's responsibility. Two different keys for the same action bypass deduplication. Hash the exact destination, payload, attachments and cost where applicable.
- A malicious writer of the database can change records. Protect the database and owner tokens outside agent write access.
- Local SQLite storage only; not a distributed/cloud coordination service. Do not use a network filesystem without validating its SQLite locking behavior.
- Operation keys, hashes and timestamps can still be sensitive metadata. Use opaque keys, protect the file and do not publish real ledgers. Raw payloads are not stored.
- No cleanup, encryption, remote executor or human reconciliation workflow. No automatic retry even when an action never started; safety trades availability for review.
