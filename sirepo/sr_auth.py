# -*- coding: utf-8 -*-
u"""authentication and authorization routines

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkinspect
from sirepo import cookie
from sirepo import sr_api_perm
from sirepo import util


login_module = None


def all_uids():
    if not login_module:
        return []
    return login_module.all_uids()


def assert_api_call(func):
    p = getattr(func, sr_api_perm.ATTR)
    a = sr_api_perm.APIPerm
    if p == a.REQUIRE_USER:
        if not cookie.has_sentinel():
            util.raise_forbidden(
                'cookie does not have a sentinel: perm={} func={}',
                p,
                func.__name__,
            )
    elif p == a.ALLOW_VISITOR:
        pass
    elif p == a.ALLOW_COOKIELESS_USER:
        cookie.set_sentinel()
        if login_module:
            login_module.allow_cookieless_user()
    elif p == a.ALLOW_LOGIN:
#TODO(robnagler) need state so that set_user can happen
        cookie.set_sentinel()
    else:
        raise AssertionError('unexpected sr_api_perm={}'.format(p))


def assert_api_def(func):
    try:
        assert isinstance(getattr(func, sr_api_perm.ATTR), sr_api_perm.APIPerm)
    except Exception as e:
        raise AssertionError(
            'function needs sr_api_perm decoration: func={} err={}'.format(
                func.__name__,
                e,
            ),
        )


def register_login_module():
    global login_module

    m = pkinspect.caller_module()
    assert not login_module, \
        'login_module already registered: old={} new={}'.format(login_module, m)
    login_module = m