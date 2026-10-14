"""Local operation reservation ledger. It never executes an operation."""
import argparse
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone


def payload_digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def connect(path):
    db=sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY, digest TEXT NOT NULL, token TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, finished_at TEXT)')
    return db


def claim(db, key, digest):
    if type(key) is not str or not key.strip() or len(key)>200:
        raise ValueError('key must be a nonempty string up to 200 characters')
    if type(digest) is not str or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('digest must be lowercase SHA-256')
    token=secrets.token_hex(24)
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT * FROM operations WHERE key=?',(key,)).fetchone()
        if row:
            result={'status':'conflict' if row['digest']!=digest else 'already-recorded', 'state':row['state']}
        else:
            db.execute('INSERT INTO operations VALUES (?,?,?,?,?,NULL)',(key,digest,token,'reserved',datetime.now(timezone.utc).isoformat()))
            result={'status':'claimed','token':token,'state':'reserved'}
        db.execute('COMMIT')
        return result
    except BaseException:
        db.execute('ROLLBACK'); raise


def finish(db, key, token, outcome):
    if outcome not in ('succeeded','uncertain') or type(outcome) is not str:
        raise ValueError('outcome must be succeeded or uncertain')
    if type(key) is not str or type(token) is not str:
        raise ValueError('key and token must be strings')
    cursor=db.execute('UPDATE operations SET state=?, finished_at=? WHERE key=? AND token=? AND state=?',
                      (outcome,datetime.now(timezone.utc).isoformat(),key,token,'reserved'))
    return {'updated':cursor.rowcount==1}


def status(db,key):
    row=db.execute('SELECT key,digest,state,created_at,finished_at FROM operations WHERE key=?',(key,)).fetchone()
    return dict(row) if row else None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',required=True)
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('claim'); c.add_argument('key'); c.add_argument('digest')
    c=sub.add_parser('finish'); c.add_argument('key'); c.add_argument('outcome',choices=['succeeded','uncertain'])
    sub.add_parser('status').add_argument('key')
    args=p.parse_args()
    try:
        with connect(args.db) as db:
            if args.command=='claim': result=claim(db,args.key,args.digest)
            elif args.command=='finish':
                import sys
                # Pipe controller-owned claim token, never place it in shell history.
                result=finish(db,args.key,sys.stdin.read().strip(),args.outcome)
            else: result=status(db,args.key)
        print(json.dumps(result))
        return 0
    except (ValueError,sqlite3.Error,OSError) as exc:
        print(json.dumps({'error':type(exc).__name__})); return 2


if __name__=='__main__': raise SystemExit(main())
