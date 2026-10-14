import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from ledger import connect,claim,finish,status,payload_digest

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=str(Path(self.tmp.name)/'ops.db')
        self.db=connect(self.path); self.digest=payload_digest({'synthetic':'example'})
    def tearDown(self): self.db.close(); self.tmp.cleanup()
    def test_claim(self): self.assertEqual(claim(self.db,'a',self.digest)['status'],'claimed')
    def test_repeat(self):
        claim(self.db,'a',self.digest); self.assertEqual(claim(self.db,'a',self.digest),{'status':'already-recorded','state':'reserved'})
    def test_conflict(self):
        claim(self.db,'a',self.digest); self.assertEqual(claim(self.db,'a','a'*64)['status'],'conflict')
    def test_finish(self):
        r=claim(self.db,'a',self.digest); self.assertTrue(finish(self.db,'a',r['token'],'succeeded')['updated'])
        self.assertEqual(status(self.db,'a')['state'],'succeeded')
    def test_wrong_token(self):
        claim(self.db,'a',self.digest); self.assertFalse(finish(self.db,'a','wrong','succeeded')['updated'])
    def test_no_finish_twice(self):
        r=claim(self.db,'a',self.digest); finish(self.db,'a',r['token'],'uncertain')
        self.assertFalse(finish(self.db,'a',r['token'],'succeeded')['updated'])
    def test_uncertain_not_reclaimed(self):
        r=claim(self.db,'a',self.digest); finish(self.db,'a',r['token'],'uncertain')
        self.assertEqual(claim(self.db,'a',self.digest)['state'],'uncertain')
    def test_survives_reopen(self):
        claim(self.db,'a',self.digest)
        with connect(self.path) as d: self.assertEqual(claim(d,'a',self.digest)['status'],'already-recorded')
    def test_token_hidden(self):
        claim(self.db,'a',self.digest); self.assertNotIn('token',status(self.db,'a'))
    def test_unknown(self): self.assertIsNone(status(self.db,'missing'))
    def test_invalid(self):
        for key,digest in [('',self.digest),('a','bad'),('a','Z'*64),(None,self.digest)]:
            with self.assertRaises(ValueError): claim(self.db,key,digest)
    def test_concurrency(self):
        def worker(_):
            db=connect(self.path)
            try: return claim(db,'race',self.digest)['status']
            finally: db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(worker,range(16)))
        self.assertEqual(results.count('claimed'),1)
    def test_digest_order(self): self.assertEqual(payload_digest({'a':1,'b':2}),payload_digest({'b':2,'a':1}))
    def test_invalid_outcome(self):
        with self.assertRaises(ValueError): finish(self.db,'a','b','retry')

if __name__=='__main__': unittest.main()
