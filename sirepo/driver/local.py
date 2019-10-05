# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
from sirepo import driver
from sirepo import job
from sirepo import job_supervisor
import functools
import os
import sirepo.mpi
import tornado.ioloop
import tornado.locks
import tornado.process


_TERMINATE_TIMEOUT_SECS = 3

cfg = None

def init_class():
    # TODO(e-carlin): cfg should be at bottom like in other modules. Except that
    # class LocalDriver needs it which means it has to be declared before it
    global cfg

    cfg = pkconfig.init(
        parallel_slots=(1, int, 'total number of parallel slots'),
        sequential_slots=(1, int, 'total number of sequential slots'),
        supervisor_uri=(
            'http://{}:{}{}'.format(job.DEFAULT_IP, job.DEFAULT_PORT, job.SERVER_URI),
            str,
            'how agents connect to supervisor',
        ),
    )
    LocalDriver.resources = PKDict(
        parallel=_Resources(cfg.parallel_slots),
        sequential=_Resources(cfg.sequential_slots),
    )
    return LocalDriver


class LocalDriver(driver.DriverBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwarg)
        self._agent = _LocalAgent(self.agent_id)

        # TODO(e-carlin): This is used to get stats about drivers as the code
        # is running. Only useful when closely debugging code. Delete when stable.
        # tornado.ioloop.IOLoop.current().spawn_callback(
        #     self._stats
        # )

    def __repr__(self):
        return ''
        return 'agent_id={} agent_started={} running_data_jobs={} requests={} resources={}'.format(
            self.agent_id,
            self.agent_started(),
            self.running_data_jobs,
            self.requests,
            self.resources,
        )

    # TODO(e-carlin): If IoLoop.spawn_callback(self._stats) is deleted then
    # this can be deleted too.
    async def _stats(self):
        import tornado.gen
        while True:
            pkdlog('{}', self)
            await tornado.gen.sleep(cfg.stats_secs)


class _LocalAgent():
    def __init__(self, agent_id):
        self.agent_started = False
        self._agent_id = agent_id
        self._agent_process = None
        self._agent_start_attempts = 0
        self._max_agent_start_attempts = 2
        self._agent_kill_requested = False
        self._wait_for_terminate_timeout = None
        self._agent_exited = tornado.locks.Event()

    def start(self, agent_error_exit_callback):
        tornado.ioloop.IOLoop.current().spawn_callback(
            self._start, agent_error_exit_callback
        )

    def kill(self):
        def _kill(self):
            pkdlog('agent_id={} killed with SIGKILL', self._agent_id)
            self._agent_process.proc.kill()

        pkdc('agent_id={}', self._agent_id)
        # TODO(e-carlin): More error handling. If terminate doesn't work
        # we need to go to kill
        # TODO(e-carlin): What happens when an exception is thrown?
        self._wait_for_terminate_timeout = tornado.ioloop.IOLoop.current().call_later(
            _TERMINATE_TIMEOUT_SECS,
            _kill, self
        )
        self._agent_kill_requested = True
        self._agent_process.proc.terminate()

    def _on_agent_exit(self, agent_error_exit_callback, returncode):
        pkdc(
            'agent_id={}, returncode={}, _agent_kill_requested={}, _agent_start_attemtps={}',
            self._agent_id,
            returncode,
            self._agent_kill_requested,
            self._agent_start_attempts,
        )
        if self._wait_for_terminate_timeout:
            tornado.ioloop.IOLoop.current().remove_timeout(
                self._wait_for_terminate_timeout
            )
        self.agent_started = False
        # if we didn't plan this exit
        if not self._agent_kill_requested or returncode != 0:
            if self._agent_start_attempts > self._max_agent_start_attempts:
                agent_error_exit_callback(returncode)
            else:
                # TODO(e-carlin): look at runner/__init__.py:203
                self.start(agent_error_exit_callback)

    def _start(self, agent_error_exit_callback):
        pkdlog('agent_id={}', self._agent_id)
        self._agent_start_attempts += 1
        # TODO(e-carlin): Make this more robust. Ex handle failures,
        # monitor the process, be able to kill it
        env = dict(os.environ)
#rn wrap this in job_subprocess()
        env['PYENV_VERSION'] = 'py3'
        env['SIREPO_PKCLI_JOB_AGENT_AGENT_ID'] = self._agent_id
        env['SIREPO_PKCLI_JOB_AGENT_SUPERVISOR_URI'] = cfg.supervisor_uri
        self._agent_process = tornado.process.Subprocess(
            [
                'pyenv',
                'exec',
                'sirepo',
                'job_agent',
                'start',
            ],
            env=env,
        )
        self._agent_process.set_exit_callback(
            functools.partial(
                self._on_agent_exit, agent_error_exit_callback,
            )
        )


class _Resources(PKDict):
    def __init__(self, total):
        self.drivers []
        self.slots = PKDict(
            total=total,
            in_use=pkcollections.Dict(),
        )
    )
