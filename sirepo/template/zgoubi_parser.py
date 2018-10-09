# -*- coding: utf-8 -*-
u"""zgoubi input file parser.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template.line_parser import LineParser
import re

_COMMAND_INDEX_POS = 115


def parse_file(zgoubi_text):
    parser = LineParser()
    lines = zgoubi_text.replace('\r', '').split('\n')
    models = {
        'beamlines': [
            {
                'name': 'BL1',
                'id': parser.next_id(),
                'items': [],
            },
        ],
        'elements': [],
    }
    # skip first documentation line
    lines.pop(0)
    parser.increment_line_number()
    current_command = None
    for line in lines:
        parser.increment_line_number()
        line = re.sub(r'\!.*$', '', line)
        line = re.sub(r'^\s+', '', line)
        if not line:
            continue
        keyword = _parse_keyword(line)
        if keyword:
            if current_command:
                _add_command(parser.next_id(), current_command, models)
            if keyword == 'END':
                current_command = None
                break
            line = _strip_command_index(line)
            current_command = [line.split()]
            current_command[0][0] = keyword
        else:
            line = line.lstrip()
            current_command.append(line.split())
    assert current_command is None, 'missing END element'
    return models


def _add_command(command_id, command, models):
    command_type = command[0][0]
    method = '_zgoubi_{}'.format(command_type).lower()
    if method not in globals():
        pkdlog('unknown zgoubi element: {}', method)
        return
    el = globals()[method](command)
    if el:
        el['id'] = command_id
        models['elements'].append(el)
        models['beamlines'][0]['items'].append(el['id'])


def _parse_command(command, command_def):
    res = _parse_command_header(command)
    for i in range(len(command_def)):
        _parse_command_line(res, command[i + 1], command_def[i])
    return res


def _parse_command_header(command):
    return _parse_command_line({}, command[0], 'type *label1 *label2')


def _parse_command_line(element, line, line_def):
    for k in line_def.split(' '):
        if k[0] == '*':
            k = k[1:]
            if not len(line):
                break;
        element[k] = line.pop(0)
    return element


def _parse_keyword(line):
    m = re.match(r"\s*'(\w+)'", line)
    if m:
        return m.group(1).upper()
    return None


def _strip_command_index(line):
    # strip the command index if present
    if len(line) > _COMMAND_INDEX_POS:
        line = re.sub(r'\s+\d+\s*$', '', line)
    return line


def _zgoubi_autoref(command):
    i = command[1][0]
    assert i == '4', '{}: only AUTOREF 4 is supported for now'.format(i)
    return _parse_command(command, [
        'I',
        'XCE YCE ALE',
    ])

def _zgoubi_changref(command):
    if re.search(r'^(X|Y|Z)', command[1][0]):
        # new format
        res = _parse_command_header(command)
        res['order'] = ' '.join(command[1])
        return res
    return _parse_command(command, [
        'XCE YCE ALE',
    ])

def _zgoubi_drift(command):
    return _parse_command(command, [
        'XL',
    ])

def _zgoubi_faisceau(command):
    return _parse_command_header(command)

def _zgoubi_marker(command):
    return _parse_command_header(command)

def _zgoubi_multipol(command):
    res = _parse_command(command, [
        'IL',
        'XL R_0 B_1 B_2 B_3 B_4 B_5 B_6 B_7 B_8 B_9 B_10',
        'X_E LAM_E E_2 E_3 E_4 E_5 E_6 E_7 E_8 E_9 E_10',
        'NCE C_0 C_1 C_2 C_3 C_4 C_5',
        'X_S LAM_S S_2 S_3 S_4 S_5 S_6 S_7 S_8 S_9 S_10',
        'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5',
        'R_1 R_2 R_3 R_4 R_5 R_6 R_7 R_8 R_9 R_10',
        'XPAS',
        'KPOS XCE YCE ALE',
    ])
    assert res['KPOS'] in ('1', '2', '3'), '{}: MULTIPOL KPOS not yet supported'.format(res['KPOS'])
    return res

def _zgoubi_objet(command):
    kobj = command[2][0]
    assert kobj == '5.1', '{}: only OBJET 5.1 is supported for now'.format(kobj)
    return _parse_command(command, [
        'BORO',
        'KOBJ',
        'dY dT dZ dP dS dD',
        'YR TR ZR PR SR DR',
        'alpha_y beta_y alpha_z beta_z alpha_s beta_s D_y Dprime_y D_z Dprime_z',
    ])

def _zgoubi_optics(command):
    return _parse_command(command, [
        'IOPT',
    ])

def _zgoubi_particul(command):
    if re.search(r'^[\-\.0-9]+', command[1][0]):
        return _parse_command(command, [
            'M Q G tau X',
        ])
    return _parse_command(command, [
        'particle_type',
    ])

def _zgoubi_scaling(command):
    #TODO(pjm): implement scaling
    return None

def _zgoubi_ymy(command):
    return _parse_command_header(command)