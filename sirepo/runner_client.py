from pykern import pkcollections
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import simulation_db
from sirepo import srdb
import aenum
import contextlib
import requests
import socket


_CHUNK_SIZE = 4096


class JobStatus(aenum.Enum):
    MISSING = 'missing'     # no data on disk, not currently running
    RUNNING = 'running'     # data on disk is incomplete but it's running
    ERROR = 'error'         # data on disk exists, but job failed somehow
    CANCELED = 'canceled'   # data on disk exists, but is incomplete
    COMPLETED = 'completed' # data on disk exists, and is fully usable


def _request(body):
    #TODO(e-carlin): uid is used to identify the proper broker for the reuqest
    # We likely need a better key and we shouldn't expose this implementation
    # detail to the client.
    uid = simulation_db.uid_from_dir_name(body['run_dir'])
    body['uid'] = uid
    body['source'] = 'server'
    r = requests.post('http://0.0.0.0:8888', json=body)
    return pkjson.load_any(r.content)

def start_report_job(run_dir, jhash, backend, cmd, tmp_dir):
    body = {
        'action': 'start_report_job',
        'run_dir': str(run_dir),
        'jhash': jhash,
        'backend': backend,
        'cmd': cmd,
        'tmp_dir': str(tmp_dir),
    }
    return _request(body)


def report_job_status(run_dir, jhash):
    body = {
        'action': 'report_job_status',
        'run_dir': str(run_dir),
        'jhash': jhash,
    }
    result = _request(body)
    return JobStatus(result.status)
    # return JobStatus('missing')


def cancel_report_job(run_dir, jhash):
    raise NotImplementedError()
    # return _rpc({
    #     'action': 'cancel_report_job', 'run_dir': str(run_dir), 'jhash': jhash,
    # })


def run_extract_job(run_dir, jhash, subcmd, *args):
    raise NotImplementedError()
    # return _rpc({
    #     'action': 'run_extract_job',
    #     'run_dir': str(run_dir),
    #     'jhash': jhash,
    #     'subcmd': subcmd,
    #     'arg': pkjson.dump_pretty(args),
    # })
