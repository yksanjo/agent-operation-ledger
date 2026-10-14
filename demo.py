import tempfile
from pathlib import Path
from ledger import connect,claim,finish,payload_digest

with tempfile.TemporaryDirectory() as folder:
    db=connect(str(Path(folder)/'demo.db'))
    digest=payload_digest({'synthetic':'no actual action'})
    r=claim(db,'fixture-1',digest)
    assert r['status']=='claimed'
    assert claim(db,'fixture-1',digest)['status']=='already-recorded'
    assert finish(db,'fixture-1',r['token'],'uncertain')['updated']
    assert claim(db,'fixture-1',digest)['state']=='uncertain'
    print('PASS: first claim wins; duplicate blocked; uncertain result never auto-retried')
    db.close()
