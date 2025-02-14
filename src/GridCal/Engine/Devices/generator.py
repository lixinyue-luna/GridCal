# This file is part of GridCal.
#
# GridCal is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GridCal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GridCal.  If not, see <http://www.gnu.org/licenses/>.

import pandas as pd
import pulp
import numpy as np
from GridCal.Engine.Devices.meta_devices import EditableDevice, DeviceType, GCProp


class Generator(EditableDevice):
    """
    Voltage controlled generator. This generators supports several reactive power
    control modes (see
    :class:`GridCal.Engine.Simulations.PowerFlow.power_flow_driver.ReactivePowerControlMode`)
    to regulate the voltage on its :ref:`bus` during
    :ref:`power flow simulations<gridcal_engine_simulations_PowerFlow>`.

    Arguments:

        **name** (str, "gen"): Name of the generator

        **active_power** (float, 0.0): Active power in MW

        **power_factor** (float, 0.8): Power factor

        **voltage_module** (float, 1.0): Voltage setpoint in per unit

        **is_controlled** (bool, True): Is the generator voltage controlled?

        **Qmin** (float, -9999): Minimum reactive power in MVAr

        **Qmax** (float, 9999): Maximum reactive power in MVAr

        **Snom** (float, 9999): Nominal apparent power in MVA

        **power_prof** (DataFrame, None): Pandas DataFrame with the active power profile in MW

        **power_factor_prof** (DataFrame, None): Pandas DataFrame with the power factor profile

        **vset_prof** (DataFrame, None): Pandas DataFrame with the voltage setpoint profile in per unit

        **active** (bool, True): Is the generator active?

        **p_min** (float, 0.0): Minimum dispatchable power in MW

        **p_max** (float, 9999): Maximum dispatchable power in MW

        **op_cost** (float, 1.0): Operational cost in Eur (or other currency) per MW

        **Sbase** (float, 100): Nominal apparent power in MVA

        **enabled_dispatch** (bool, True): Is the generator enabled for OPF?

        **mttf** (float, 0.0): Mean time to failure in hours

        **mttr** (float, 0.0): Mean time to recovery in hours

    """

    def __init__(self, name='gen', active_power=0.0, power_factor=0.8, voltage_module=1.0, is_controlled=True,
                 Qmin=-9999, Qmax=9999, Snom=9999, power_prof=None, power_factor_prof=None, vset_prof=None,
                 Cost_prof=None, active=True,
                 p_min=0.0, p_max=9999.0, op_cost=1.0, Sbase=100, enabled_dispatch=True, mttf=0.0, mttr=0.0):

        EditableDevice.__init__(self,
                                name=name,
                                active=active,
                                device_type=DeviceType.GeneratorDevice,
                                editable_headers={'name': GCProp('', str, 'Name of the generator'),
                                                  'bus': GCProp('', None, 'Connection bus name'),
                                                  'active': GCProp('', bool, 'Is the generator active?'),
                                                  'is_controlled': GCProp('', bool,
                                                                          'Is this generator voltage-controlled?'),
                                                  'P': GCProp('MW', float, 'Active power'),
                                                  'Pf': GCProp('', float,
                                                               'Power factor (cos(fi)). '
                                                               'This is used for non-controlled generators.'),
                                                  'Vset': GCProp('p.u.', float,
                                                                 'Set voltage. '
                                                                 'This is used for controlled generators.'),
                                                  'Snom': GCProp('MVA', float, 'Nomnial power.'),
                                                  'Qmin': GCProp('MVAr', float, 'Minimum reactive power.'),
                                                  'Qmax': GCProp('MVAr', float, 'Maximum reactive power.'),
                                                  'Pmin': GCProp('MW', float, 'Minimum active power. Used in OPF.'),
                                                  'Pmax': GCProp('MW', float, 'Maximum active power. Used in OPF.'),
                                                  'Cost': GCProp('e/MWh', float, 'Generation unitary cost. Used in OPF.'),
                                                  'enabled_dispatch': GCProp('', bool,
                                                                             'Enabled for dispatch? Used in OPF.'),
                                                  'mttf': GCProp('h', float, 'Mean time to failure'),
                                                  'mttr': GCProp('h', float, 'Mean time to recovery')},
                                non_editable_attributes=list(),
                                properties_with_profile={'P': 'P_prof',
                                                         'Pf': 'Pf_prof',
                                                         'Vset': 'Vset_prof',
                                                         'Cost': 'Cost_prof'})

        self.bus = None

        self.mttf = mttf

        self.mttr = mttr

        # is the device active active power dispatch?
        self.enabled_dispatch = enabled_dispatch

        # Power (MVA)
        self.P = active_power

        # Power factor
        self.Pf = power_factor

        # voltage set profile for this load in p.u.
        self.Pf_prof = power_factor_prof

        # If this generator is voltage controlled it produces a PV node, otherwise the node remains as PQ
        self.is_controlled = is_controlled

        # Nominal power in MVA (also the machine base)
        self.Snom = Snom

        # Minimum dispatched power in MW
        self.Pmin = p_min

        # Maximum dispatched power in MW
        self.Pmax = p_max

        # power profile for this load in MW
        self.P_prof = power_prof

        # Voltage module set point (p.u.)
        self.Vset = voltage_module

        # voltage set profile for this load in p.u.
        self.Vset_prof = vset_prof

        # minimum reactive power in MVAr
        self.Qmin = Qmin

        # Maximum reactive power in MVAr
        self.Qmax = Qmax

        # Cost of operation €/MW
        self.Cost = op_cost

        self.Cost_prof = Cost_prof

        # Dynamic vars
        # self.Ra = Ra
        # self.Xa = Xa
        # self.Xd = Xd
        # self.Xq = Xq
        # self.Xdp = Xdp
        # self.Xqp = Xqp
        # self.Xdpp = Xdpp
        # self.Xqpp = Xqpp
        # self.Td0p = Td0p
        # self.Tq0p = Tq0p
        # self.Td0pp = Td0pp
        # self.Tq0pp = Tq0pp
        # self.H = H
        # self.speed_volt = speed_volt
        # self.base_mva = base_mva  # machine base MVA

        # system base power MVA
        self.Sbase = Sbase

        # Linear problem generator dispatch power variable (in p.u.)
        self.lp_name = self.type_name + '_' + self.name + str(id(self))

        # variable to dispatch the power in a Linear program
        self.LPVar_P = pulp.LpVariable(self.lp_name + '_P', self.Pmin / self.Sbase, self.Pmax / self.Sbase)

        # list of variables of active power dispatch in a series of linear programs
        self.LPVar_P_prof = None

    def copy(self):
        """
        Make a deep copy of this object
        :return: Copy of this object
        """

        # make a new instance (separated object in memory)
        gen = Generator()

        gen.name = self.name

        # Power (MVA)
        # MVA = kV * kA
        gen.P = self.P

        # is the generator active?
        gen.active = self.active

        # power profile for this load
        gen.P_prof = self.P_prof

        # Power factor profile
        gen.Pf_prof = self.Pf_prof

        # Voltage module set point (p.u.)
        gen.Vset = self.Vset

        # voltage set profile for this load
        gen.Vset_prof = self.Vset_prof

        # minimum reactive power in per unit
        gen.Qmin = self.Qmin

        # Maximum reactive power in per unit
        gen.Qmax = self.Qmax

        # Nominal power
        gen.Snom = self.Snom

        # is the generator enabled for dispatch?
        gen.enabled_dispatch = self.enabled_dispatch

        gen.mttf = self.mttf

        gen.mttr = self.mttr

        return gen

    def get_json_dict(self, id, bus_dict):
        """
        Get json dictionary
        :param id: ID: Id for this object
        :param bus_dict: Dictionary of buses [object] -> ID
        :return: json-compatible dictionary
        """
        return {'id': id,
                'type': 'controlled_gen',
                'phases': 'ps',
                'name': self.name,
                'bus': bus_dict[self.bus],
                'active': self.active,
                'is_controlled': self.is_controlled,
                'P': self.P,
                'Pf': self.Pf,
                'vset': self.Vset,
                'Snom': self.Snom,
                'qmin': self.Qmin,
                'qmax': self.Qmax,
                'Pmin': self.Pmin,
                'Pmax': self.Pmax,
                'Cost': self.Cost}

    def initialize_lp_vars(self):
        """
        Initialize the LP variables
        """
        self.lp_name = self.type_name + '_' + self.name + str(id(self))

        self.LPVar_P = pulp.LpVariable(self.lp_name + '_P', self.Pmin / self.Sbase, self.Pmax / self.Sbase)

    def get_lp_var_profile(self, index):
        """
        Get the profile of the LP solved values into a Pandas DataFrame
        :param index: time index
        :return: DataFrame with the LP values
        """
        dta = [x.value() for x in self.LPVar_P_prof]
        return pd.DataFrame(data=dta, index=index, columns=[self.name])

    def apply_lp_vars(self, at=None):
        """
        Set the LP vars to the main value or the profile
        """
        if self.LPVar_P is not None:
            if at is None:
                self.P = self.LPVar_P.value()
            else:
                self.P_prof.values[at] = self.LPVar_P.value()

    def apply_lp_profile(self, Sbase):
        """
        Set LP profile to the regular profile
        :return:
        """
        n = self.P_prof.shape[0]
        if self.active and self.enabled_dispatch:
            for i in range(n):
                self.P_prof.values[i] = self.LPVar_P_prof[i].value() * Sbase
        else:
            # there are no values in the LP vars because this generator is deactivated,
            # therefore fill the profiles with zeros when asked to copy the lp vars to the power profiles
            self.P_prof.values = np.zeros(self.P_prof.shape[0])

