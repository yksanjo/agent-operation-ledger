"""16 local synthetic workers, one reservation. Does not execute a side effect."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from ledger import connect, claim, payload_digest

with TemporaryDirectory() as folder:
    path=str(Path(folder)/'race.db')
    setup=connect(path); setup.close()
    def worker(index):
        db=connect(path)
        try: return claim(db,'fixture-operation',payload_digest({'synthetic':'same-action'}))['status']
        finally: db.close()
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(worker,range(16)))
    winners=results.count('claimed')
    blocked=results.count('already-recorded')
    assert (winners,blocked)==(1,15)
    print(f'16 workers: {winners} claim won, {blocked} duplicates blocked')
    print('No external action executed.');
