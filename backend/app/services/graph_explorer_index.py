"""Offline adjacency indexing only: no ML, features or NetworkX centrality."""
from collections import deque
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import time

VERSION = 'canonical-directed-amount-v1'
INDEX_SCHEMA = 'graphfin-topology-index-v1'
SCOPE_LIMIT = 600


def file_hash(path):
    digest = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def build_index(source, destination, dataset_id, expected_hash, score_seeds, diagnostic_seeds=()):
    """Match research load_input filtering and GraphService sequential weights.

    IDs and events remain private server storage. Output is an exclusive new
    artifact; never call this function from an HTTP request.
    """
    import numpy as np
    import pandas as pd
    source, destination = Path(source), Path(destination)
    if file_hash(source) != expected_hash:
        raise ValueError('Source bytes differ from approved dataset.')
    if destination.exists():
        raise FileExistsError(destination)
    start = time.perf_counter()
    conn = sqlite3.connect(destination)
    conn.executescript('''
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
      CREATE TABLE events(s TEXT,t TEXT,amount REAL,ts REAL);
      CREATE TABLE edges(s TEXT,t TEXT,amount REAL,cnt INTEGER,first REAL,last REAL,PRIMARY KEY(s,t)) WITHOUT ROWID;
      CREATE TABLE nodes(id TEXT PRIMARY KEY,in_degree INTEGER,out_degree INTEGER,neighbors INTEGER,received REAL,sent REAL) WITHOUT ROWID;
    ''')
    identities = set(); rows = retained = 0
    minimum = float('inf'); maximum = -float('inf')
    try:
        for frame in pd.read_csv(source, dtype={'sender_id':str,'receiver_id':str,'transaction_id':str},chunksize=50000):
            required = ['transaction_id','sender_id','receiver_id','amount','timestamp']
            if not set(required).issubset(frame) or frame[required].isna().any().any():
                raise ValueError('Canonical transaction schema failed.')
            ids = frame.transaction_id.tolist()
            if len(set(ids))!=len(ids) or identities.intersection(ids):
                raise ValueError('Duplicate transaction identity.')
            identities.update(ids); rows += len(frame)
            frame.amount = pd.to_numeric(frame.amount,errors='raise')
            if not np.isfinite(frame.amount).all():
                raise ValueError('Nonfinite amount.')
            timestamps = pd.to_datetime(frame.timestamp,errors='raise',utc=True)
            valid = (frame.amount>0) & (frame.sender_id!=frame.receiver_id)
            timestamps = timestamps[valid].astype('datetime64[ns, UTC]').astype('int64') / 1e9
            frame = frame[valid]
            batch = list(zip(frame.sender_id, frame.receiver_id, frame.amount, timestamps))
            conn.executemany('INSERT INTO events VALUES(?,?,?,?)',batch)
            # Same float addition order as GraphService's original input loop.
            conn.executemany('''INSERT INTO edges VALUES(?,?,?,1,?,?) ON CONFLICT(s,t) DO UPDATE SET
                amount=edges.amount+excluded.amount,cnt=edges.cnt+1,
                first=MIN(edges.first,excluded.first),last=MAX(edges.last,excluded.last)''',
                ((u,v,float(a),float(ts),float(ts)) for u,v,a,ts in batch))
            retained += len(batch)
            if len(timestamps):
                minimum=min(minimum,float(timestamps.min())); maximum=max(maximum,float(timestamps.max()))
        conn.executescript('''
          CREATE INDEX edge_target ON edges(t,s);
          CREATE INDEX event_source ON events(s,ts,t);
          CREATE INDEX event_target ON events(t,ts,s);
          INSERT INTO nodes
          WITH ids AS (SELECT s id FROM edges UNION SELECT t id FROM edges),
            ins AS (SELECT t id,COUNT(*) degree,SUM(amount) amount FROM edges GROUP BY t),
            outs AS (SELECT s id,COUNT(*) degree,SUM(amount) amount FROM edges GROUP BY s),
            adj AS (SELECT s id,t peer FROM edges UNION SELECT t id,s peer FROM edges),
            ns AS (SELECT id,COUNT(*) degree FROM adj GROUP BY id)
          SELECT ids.id,COALESCE(ins.degree,0),COALESCE(outs.degree,0),ns.degree,
            ROUND(COALESCE(ins.amount,0),2),ROUND(COALESCE(outs.amount,0),2)
          FROM ids LEFT JOIN ins USING(id) LEFT JOIN outs USING(id) LEFT JOIN ns USING(id);
        ''')
        anchors = []
        for account in score_seeds[:20]:
            if conn.execute('SELECT 1 FROM nodes WHERE id=?',(account,)).fetchone():
                anchors.append((account,'saved E4 top-20 anchor'))
        for account in diagnostic_seeds:
            if conn.execute('SELECT 1 FROM nodes WHERE id=?',(account,)).fetchone() and account not in {x[0] for x in anchors}:
                anchors.append((account,'saved diagnostic anchor'))
        for order, role in [('DESC','high-degree anchor'),('ASC','low-degree anchor')]:
            row = conn.execute(f'SELECT id FROM nodes WHERE neighbors>0 ORDER BY (in_degree+out_degree) {order},id LIMIT 1').fetchone()
            if row and row[0] not in {x[0] for x in anchors}:
                anchors.append((row[0],role))
        scope = {x[0] for x in anchors}; queue = deque(sorted(scope))
        while queue and len(scope)<SCOPE_LIMIT:
            account=queue.popleft()
            peers=conn.execute('SELECT s,t FROM edges WHERE s=? OR t=? ORDER BY s,t LIMIT 601',(account,account)).fetchall()
            for peer in sorted({v if u==account else u for u,v in peers}):
                if peer not in scope:
                    scope.add(peer); queue.append(peer)
                    if len(scope)>=SCOPE_LIMIT:break
        conn.commit()
        metadata = dict(schema_version=INDEX_SCHEMA,version=VERSION,dataset_id=dataset_id,
                        dataset_sha256=expected_hash,source_rows=rows,retained_rows=retained,
                        total_nodes=conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0],
                        total_edges=conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0],
                        time_start=minimum,time_end=maximum,approved_nodes=sorted(scope),
                        scope_identity=sha256(canonical(sorted(scope))).hexdigest(),
                        anchors=[{'account':a,'role':r} for a,r in anchors])
    finally:
        conn.close()
    if file_hash(source)!=expected_hash:
        raise ValueError('Source changed while indexing.')
    metadata['index_sha256']=file_hash(destination)
    metadata['graph_id']=dataset_id+'-'+metadata['index_sha256'][:20]
    metadata['build_seconds']=time.perf_counter()-start
    return metadata
