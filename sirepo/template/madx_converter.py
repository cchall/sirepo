# -*- coding: utf-8 -*-
u"""Convert codes to/from MAD-X.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import madx_parser
from sirepo.template.lattice import LatticeUtil
import copy
import sirepo.sim_data

class MadxConverter():

    _MADX_VARIABLES = PKDict(
        twopi='pi * 2',
        raddeg='180 / pi',
        degrad='pi / 180',
    )

    def __init__(self, sim_type, field_map, downcase_variables=False):
        self.sim_type = sim_type
        self.downcase_variables = downcase_variables
        self.full_field_map = self._build_field_map(field_map)

    def from_madx(self, data):
        from sirepo.template import madx
        self.to_class = sirepo.sim_data.get_class(self.sim_type)
        self.from_class = sirepo.sim_data.get_class(madx.SIM_TYPE)
        self.field_map = self.full_field_map.from_madx
        self.drift_type = 'DRIFT'
        return self._convert(data)

    def from_madx_text(self, text):
        return self.from_madx(madx_parser.parse_file(text, self.downcase_variables))

    def to_madx(self, data):
        from sirepo.template import madx
        self.to_class = sirepo.sim_data.get_class(madx.SIM_TYPE)
        self.from_class = sirepo.sim_data.get_class(self.sim_type)
        self.field_map = self.full_field_map.to_madx
        self.drift_type = self.full_field_map.from_madx.DRIFT[0]
        return self._convert(data)

    def to_madx_text(self, data):
        from sirepo.template import madx
        return madx.python_source_for_model(self.to_madx(data), None)

    def _build_field_map(self, field_map):
        res = PKDict(
            from_madx=PKDict(),
            to_madx=PKDict(),
        )
        for el in field_map:
            madx_name = el[0]
            res.from_madx[madx_name] = el[1]
            for idx in range(1, len(el)):
                fields = copy.copy(el[idx])
                name = fields[0]
                if name not in res.to_madx:
                    fields[0] = madx_name
                    res.to_madx[name] = fields
        return res

    def _convert(self, data):
        self.result = simulation_db.default_data(self.to_class.sim_type())
        self._copy_beamlines(data)
        self._copy_elements(data)
        self._copy_code_variables(data)
        LatticeUtil(
            self.result,
            self.to_class.schema(),
        ).sort_elements_and_beamlines()
        return self.result

    def _copy_beamlines(self, data):
        for bl in data.models.beamlines:
            self.result.models.beamlines.append(PKDict(
                name=bl.name,
                items=bl['items'],
                id=bl.id,
            ))
        for f in ('name', 'visualizationBeamlineId', 'activeBeamlineId'):
            if f in data.models.simulation:
                self.result.models.simulation[f] = data.models.simulation[f]

    def _copy_code_variables(self, data):
        res = data.models.rpnVariables
        if self.to_class.sim_type() in ('madx', 'opal'):
            res = list(filter(lambda x: x.name not in self._MADX_VARIABLES, res))
        else:
            names = set([v.name for v in res])
            for name in self._MADX_VARIABLES:
                if name not in names:
                    res.append(PKDict(
                        name=name,
                        value=self._MADX_VARIABLES[name],
                    ))
        self.result.models.rpnVariables = res

    def _copy_elements(self, data):
        for el in data.models.elements:
            if el.type not in self.field_map:
                pkdlog('Unhandled element type: {}', el.type)
                el.type = self.drift_type
                if 'l' not in el:
                    el.l = 0
            fields = self.field_map[el.type]
            values = PKDict(
                name=el.name,
                type=fields[0],
                _id=el._id,
            )
            for idx in range(1, len(fields)):
                f1 = f2 = fields[idx]
                if '=' in fields[idx]:
                    f1, f2 = fields[idx].split('=')
                    if self.to_class.sim_type()  == 'madx':
                        f2, f1 = f1, f2
                values[f1] = el[f2]
            self._fixup_element(el, values)
            self.to_class.update_model_defaults(values, values.type)
            self.result.models.elements.append(values)

    def _find_var(self, data, name):
        name = self._var_name(name)
        for v in data.models.rpnVariables:
            if v.name == name:
                return v
        return None

    def _fixup_element(self, element_in, element_out):
        pass

    def _replace_var(self, data, name, value):
        v = self._find_var(data, name)
        if v:
            v.value = value
        else:
            data.models.rpnVariables.append(PKDict(
                name=self._var_name(name),
                value=value,
            ))

    def _var_name(self, name):
        return f'sr_{name}'
