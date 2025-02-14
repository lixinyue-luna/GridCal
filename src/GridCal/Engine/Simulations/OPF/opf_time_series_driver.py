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
import numpy as np
from numpy import complex, zeros,  array
import datetime
from matplotlib import pyplot as plt
from PySide2.QtCore import QThread, Signal

from GridCal.Engine.basic_structures import TimeGrouping, get_time_groups
from GridCal.Engine.Core.multi_circuit import MultiCircuit
from GridCal.Engine.plot_config import LINEWIDTH
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import SolverType
from GridCal.Engine.Simulations.OPF.opf_driver import OptimalPowerFlowResults, OptimalPowerFlowOptions
from GridCal.Engine.Simulations.OPF.dc_opf_ts import OpfDcTimeSeries
from GridCal.Engine.Simulations.OPF.ac_opf_ts import OpfAcTimeSeries
from GridCal.Engine.Simulations.OPF.ac_opf import AcOpf
from GridCal.Engine.Simulations.OPF.dc_opf import DcOpf
from GridCal.Engine.Simulations.OPF.nelder_mead_opf import AcOpfNelderMead
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import PowerFlowOptions
from GridCal.Engine.Simulations.result_types import ResultTypes


class OptimalPowerFlowTimeSeriesResults:

    def __init__(self, n, m, nt, ngen=0, nbat=0, nload=0, time=None, is_dc=False):
        """
        OPF Time Series results constructor
        :param n: number of buses
        :param m: number of branches
        :param nt: number of time steps
        :param time: Time array (optional)
        """
        self.n = n

        self.m = m

        self.nt = nt

        self.time = time

        self.voltage = zeros((nt, n), dtype=complex)

        self.load_shedding = zeros((nt, nload), dtype=float)

        self.loading = zeros((nt, m), dtype=float)

        self.losses = zeros((nt, m), dtype=float)

        self.overloads = zeros((nt, m), dtype=float)

        self.Sbus = zeros((nt, n), dtype=complex)

        self.shadow_prices = zeros((nt, n), dtype=float)

        self.Sbranch = zeros((nt, m), dtype=complex)

        self.bus_types = zeros(n, dtype=int)

        # self.available_results = ['Bus voltage', 'Bus power', 'Branch power',
        #                           'Branch loading', 'Branch overloads', 'Load shedding',
        #                           'Controlled generators power', 'Batteries power']

        self.available_results = [ResultTypes.BusVoltageModule,
                                  ResultTypes.BusVoltageAngle,
                                  ResultTypes.ShadowPrices,
                                  ResultTypes.BranchPower,
                                  ResultTypes.BranchLoading,
                                  ResultTypes.BranchOverloads,
                                  ResultTypes.LoadShedding,
                                  ResultTypes.ControlledGeneratorShedding,
                                  ResultTypes.ControlledGeneratorPower,
                                  ResultTypes.BatteryPower,
                                  ResultTypes.BatteryEnergy]

        # self.generators_power = zeros((ng, nt), dtype=complex)

        self.controlled_generator_power = np.zeros((nt, ngen), dtype=float)

        self.controlled_generator_shedding = np.zeros((nt, ngen), dtype=float)

        self.battery_power = np.zeros((nt, nbat), dtype=float)

        self.battery_energy = np.zeros((nt, nbat), dtype=float)

        self.converged = np.empty(nt, dtype=bool)

    def init_object_results(self, ngen, nbat):
        """
        declare the generator results. This is done separately since these results are known at the end of the simulation
        :param ngen: number of generators
        :param nbat: number of batteries
        """
        self.controlled_generator_power = np.zeros((self.nt, ngen), dtype=float)

        self.battery_power = np.zeros((self.nt, nbat), dtype=float)

    def set_at(self, t, res: OptimalPowerFlowResults):
        """
        Set the results
        :param t: time index
        :param res: OptimalPowerFlowResults instance
        """

        self.voltage[t, :] = res.voltage

        self.load_shedding[t, :] = res.load_shedding

        self.loading[t, :] = np.abs(res.loading)

        self.overloads[t, :] = np.abs(res.overloads)

        self.losses[t, :] =np.abs(res.losses)

        self.Sbus[t, :] = res.Sbus

        self.Sbranch[t, :] = res.Sbranch

    def plot(self, result_type, ax=None, indices=None, names=None):
        """
        Plot the results
        :param result_type:
        :param ax:
        :param indices:
        :param names:
        :return:
        """
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        if indices is None:
            indices = array(range(len(names)))

        if len(indices) > 0:
            labels = names[indices]
            y_label = ''
            title = ''
            if result_type == ResultTypes.BusVoltageModule:
                y = np.abs(self.voltage[:, indices])
                y_label = '(p.u.)'
                title = 'Bus voltage module'

            elif result_type == ResultTypes.BusVoltageAngle:
                y = np.angle(self.voltage[:, indices])
                y_label = '(Radians)'
                title = 'Bus voltage angle'

            elif result_type == ResultTypes.ShadowPrices:
                y = self.shadow_prices[:, indices]
                y_label = '(currency)'
                title = 'Bus shadow prices'

            elif result_type == ResultTypes.BranchPower:
                y = self.Sbranch[:, indices].real
                y_label = '(MW)'
                title = 'Branch power '

            elif result_type == ResultTypes.BusPower:
                y = self.Sbus[:, indices].real
                y_label = '(MW)'
                title = 'Bus power '

            elif result_type == ResultTypes.BranchLoading:
                y = np.abs(self.loading[:, indices] * 100.0)
                y_label = '(%)'
                title = 'Branch loading '

            elif result_type == ResultTypes.BranchOverloads:
                y = np.abs(self.overloads[:, indices])
                y_label = '(MW)'
                title = 'Branch overloads '

            elif result_type == ResultTypes.BranchLosses:
                y = self.losses[:, indices].real
                y_label = '(MW)'
                title = 'Branch losses '

            elif result_type == ResultTypes.LoadShedding:
                y = self.load_shedding[:, indices]
                y_label = '(MW)'
                title = 'Load shedding'

            elif result_type == ResultTypes.ControlledGeneratorPower:
                y = self.controlled_generator_power[:, indices]
                y_label = '(MW)'
                title = 'Controlled generator power'

            elif result_type == ResultTypes.ControlledGeneratorShedding:
                y = self.controlled_generator_shedding[:, indices]
                y_label = '(MW)'
                title = 'Controlled generator power'

            elif result_type == ResultTypes.BatteryPower:
                y = self.battery_power[:, indices]
                y_label = '(MW)'
                title = 'Battery power'

            elif result_type == ResultTypes.BatteryEnergy:
                y = self.battery_energy[:, indices]
                y_label = '(MWh)'
                title = 'Battery energy'

            else:
                pass

            if self.time is not None:
                df = pd.DataFrame(data=y, columns=labels, index=self.time)
            else:
                df = pd.DataFrame(data=y, columns=labels)

            df.fillna(0, inplace=True)

            if len(df.columns) > 10:
                df.plot(ax=ax, linewidth=LINEWIDTH, legend=False)
            else:
                df.plot(ax=ax, linewidth=LINEWIDTH, legend=True)

            ax.set_title(title)
            ax.set_ylabel(y_label)
            ax.set_xlabel('Time')

            return df

        else:
            return None


class SequentialOptimalPowerFlowTimeSeries(QThread):
    progress_signal = Signal(float)
    progress_text = Signal(str)
    done_signal = Signal()

    def __init__(self, grid: MultiCircuit, options: OptimalPowerFlowOptions, start_=0, end_=None):
        """
        OPF time series constructor
        :param grid: MultiCircuit instance
        :param options: OPF options instance
        """
        QThread.__init__(self)

        self.options = options

        self.grid = grid

        self.results = None

        self.start_ = start_

        self.end_ = end_

        self.logger = list()

        self.__cancel__ = False

    def get_steps(self):
        """
        Get time steps list of strings
        """
        return [l.strftime('%d-%m-%Y %H:%M') for l in pd.to_datetime(self.grid.time_profile)]

    def initialize_lp_vars(self):
        """
        initialize all the bus LP profiles
        :return:
        """
        for bus in self.grid.buses:
            bus.initialize_lp_profiles()

    def run(self):
        """
        Run the time series simulation
        @return:
        """

        numerical_circuit = self.grid.compile()
        islands = numerical_circuit.compute()

        if self.grid.time_profile is not None:

            # declare the results
            self.results = OptimalPowerFlowTimeSeriesResults(n=len(self.grid.buses),
                                                             m=len(self.grid.branches),
                                                             nt=len(self.grid.time_profile),
                                                             ngen=len(self.grid.get_generators()),
                                                             nbat=len(self.grid.get_batteries()),
                                                             nload=len(self.grid.get_loads()),
                                                             time=self.grid.time_profile)

            self.results.bus_types = numerical_circuit.bus_types

            # declare LP problem
            if self.options.solver == SolverType.DC_OPF:
                # DC optimal power flow
                problem = DcOpf(self.grid, verbose=False,
                                allow_load_shedding=self.options.load_shedding,
                                allow_generation_shedding=self.options.generation_shedding)

            # elif self.options.solver == SolverType.DYCORS_OPF:
            #
            #     problem = AcOpfDYCORS(self.grid, verbose=False)

            elif self.options.solver == SolverType.NELDER_MEAD_OPF:

                if self.options.power_flow_options is None:
                    options = PowerFlowOptions(SolverType.LACPF, verbose=False,
                                               initialize_with_existing_solution=False,
                                               multi_core=False, dispatch_storage=True, control_q=False, control_taps=False)
                else:
                    options = self.options.power_flow_options

                problem = AcOpfNelderMead(self.grid, options, verbose=False)

            elif self.options.solver == SolverType.AC_OPF:
                # AC optimal power flow
                problem = AcOpf(self.grid, verbose=False,
                                allow_load_shedding=self.options.load_shedding,
                                allow_generation_shedding=self.options.generation_shedding)

            else:
                self.logger.append('Not implemented method ' + str(self.options.solver))

            # build
            problem.build_solvers()

            batteries = self.grid.get_batteries()
            nbat = len(batteries)
            E = np.zeros(nbat)
            E0 = np.zeros(nbat)
            minE = np.zeros(nbat)
            maxE = np.zeros(nbat)

            if self.options.control_batteries and (self.end_ - self.start_) > 1:
                control_batteries = True
                for i, bat in enumerate(batteries):
                    E0[i] = bat.Enom * bat.soc_0
                    minE[i] = bat.min_soc * bat.Enom
                    maxE[i] = bat.max_soc * bat.Enom
                E = E0.copy()
            else:
                control_batteries = False  # all vectors declared already

            t = self.start_
            bat_idx = []
            force_batteries_to_charge = False
            dt = 0

            execution_avg_time = 0
            time_summation = 0
            alpha = 0.2
            while t < self.end_ and not self.__cancel__:

                start_time = datetime.datetime.now()

                problem.set_state_at(t, force_batteries_to_charge=force_batteries_to_charge,
                                     bat_idx=bat_idx, battery_loading_pu=0.01,
                                     Emin=minE/self.grid.Sbase, Emax=maxE/self.grid.Sbase,
                                     E=E/self.grid.Sbase, dt=dt)
                problem.solve(verbose=False)

                if problem.converged:
                    # gather the results
                    # get the branch flows (it is used more than one time)
                    Sbr = problem.get_branch_flows()
                    ld = problem.get_load_shedding().real
                    ld[ld == None] = 0
                    bt = problem.get_batteries_power()
                    bt[bt == None] = 0
                    gn = problem.get_controlled_generation()
                    gn[gn==None] = 0
                    gs = problem.get_generation_shedding()
                    gs[gs == None] = 0

                    self.results.voltage[t, :] = problem.get_voltage()
                    self.results.load_shedding[t, :] = ld * self.grid.Sbase.real
                    self.results.controlled_generator_shedding[t, :] = gs * self.grid.Sbase
                    self.results.battery_power[t, :] = bt * self.grid.Sbase
                    self.results.controlled_generator_power[t, :] = gn * self.grid.Sbase
                    self.results.Sbranch[t, :] = Sbr
                    self.results.overloads[t, :] = problem.get_overloads().real
                    self.results.loading[t, :] = problem.get_loading().real
                    self.results.converged[t] = bool(problem.converged)

                    # control batteries energy
                    if control_batteries and t > self.start_:
                        dt = (self.grid.time_profile[t] - self.grid.time_profile[t - 1]).seconds / 3600  # time delta in hours
                        dE = self.results.battery_power[t, :] * dt
                        E -= dE  # negative power(charge) -> more energy
                        too_low = E <= minE
                        bat_idx = np.where(too_low == True)[0]  # check which energy values are less or equal to zero
                        force_batteries_to_charge = bool(len(bat_idx))

                    self.results.battery_energy[t, :] = E
                else:
                    print('\nDid not converge!\n')

                end_time = datetime.datetime.now()
                time_elapsed = end_time - start_time
                time_summation += time_elapsed.microseconds * 1e-6
                execution_avg_time = (int(time_summation) / (t - self.start_ + 1)) * alpha + execution_avg_time * (1-alpha)
                remaining = (self.end_ - t) * execution_avg_time

                progress = ((t - self.start_ + 1) / (self.end_ - self.start_)) * 100
                self.progress_signal.emit(progress)
                self.progress_text.emit('Solving OPF at ' + str(self.grid.time_profile[t]) +
                                        '\t remaining: ' + str(datetime.timedelta(seconds=remaining)) +
                                        '\tConverged:' + str(bool(problem.converged)))
                t += 1

        else:
            print('There are no profiles')
            self.progress_text.emit('There are no profiles')

        # send the finnish signal
        self.progress_signal.emit(0.0)
        self.progress_text.emit('Done!')
        self.done_signal.emit()

    def cancel(self):
        """
        Set the cancel state
        """
        self.__cancel__ = True
        self.progress_signal.emit(0.0)
        self.progress_text.emit('Cancelled!')
        self.done_signal.emit()


class OptimalPowerFlowTimeSeries(QThread):
    progress_signal = Signal(float)
    progress_text = Signal(str)
    done_signal = Signal()

    def __init__(self, grid: MultiCircuit, options: OptimalPowerFlowOptions, start_=0, end_=None):
        """
        PowerFlow class constructor
        @param grid: MultiCircuit Object
        @param options: OPF options
        """
        QThread.__init__(self)

        # Grid to run a power flow in
        self.grid = grid

        self.numerical_circuit = self.grid.compile()

        # Options to use
        self.options = options

        # OPF results
        self.results = OptimalPowerFlowTimeSeriesResults(n=len(self.grid.buses),
                                                         m=len(self.grid.branches),
                                                         nt=len(self.grid.time_profile),
                                                         ngen=len(self.grid.get_generators()),
                                                         nbat=len(self.grid.get_batteries()),
                                                         nload=len(self.grid.get_loads()),
                                                         time=self.grid.time_profile)

        self.start_ = start_

        self.end_ = end_

        self.logger = list()

        # set cancel state
        self.__cancel__ = False

        self.all_solved = True

    def reset_results(self):
        """
        Clears the results
        """
        # reinitialize
        self.results = OptimalPowerFlowTimeSeriesResults(n=len(self.grid.buses),
                                                         m=len(self.grid.branches),
                                                         nt=len(self.grid.time_profile),
                                                         ngen=len(self.grid.get_generators()),
                                                         nbat=len(self.grid.get_batteries()),
                                                         nload=len(self.grid.get_loads()),
                                                         time=self.grid.time_profile)

    def get_steps(self):
        """
        Get time steps list of strings
        """
        return [l.strftime('%d-%m-%Y %H:%M') for l in pd.to_datetime(self.grid.time_profile)]

    def opf(self, start_, end_, remote=False):
        """
        Run a power flow for every circuit
        @return: OptimalPowerFlowResults object
        """

        if not remote:
            self.progress_signal.emit(0.0)
            self.progress_text.emit('Running all in an external solver, this may take a while...')

        if self.options.solver == SolverType.DC_OPF:

            # DC optimal power flow
            problem = OpfDcTimeSeries(numerical_circuit=self.numerical_circuit,
                                      start_idx=start_, end_idx=end_)

        elif self.options.solver == SolverType.AC_OPF:

            # DC optimal power flow
            problem = OpfAcTimeSeries(numerical_circuit=self.numerical_circuit,
                                      start_idx=start_, end_idx=end_)

        else:
            self.logger.append('Solver not supported in this mode: ' + str(self.options.solver))
            return

        status = problem.solve()
        print("Status:", status)

        a = start_
        b = end_
        self.results.voltage[a:b, :] = problem.get_voltage()
        self.results.load_shedding[a:b, :] = problem.get_load_shedding()
        self.results.battery_power[a:b, :] = problem.get_battery_power()
        self.results.battery_energy[a:b, :] = problem.get_battery_energy()
        self.results.controlled_generator_power[a:b, :] = problem.get_generator_power()
        self.results.Sbranch[a:b, :] = problem.get_branch_power()
        self.results.overloads[a:b, :] = problem.get_overloads()
        self.results.loading[a:b, :] = problem.get_loading()
        self.results.shadow_prices[a:b, :] = problem.get_shadow_prices()

        return self.results

    def opf_by_groups(self):
        """
        Run the OPF by groups
        """

        self.progress_signal.emit(0.0)
        self.progress_text.emit('Making groups...')

        # get the partition points of the time series
        groups = get_time_groups(t_array=self.grid.time_profile, grouping=self.options.grouping)

        n = len(groups)
        i = 1
        while i < n and not self.__cancel__:

            start_ = groups[i-1]
            end_ = groups[i]

            if start_ >= self.start_ and end_ <= self.end_:

                # run an opf for the group interval only if the group is within the start:end boundaries
                self.opf(start_=start_, end_=end_, remote=True)

            self.progress_text.emit('Running OPF for the time group ' + str(i) + ' in external solver...')
            progress = ((start_ - self.start_ + 1) / (self.end_ - self.start_)) * 100
            self.progress_signal.emit(progress)

            i += 1

    def run(self):
        """

        :return:
        """
        if self.options.grouping == TimeGrouping.NoGrouping:
            self.opf(start_=self.start_, end_=self.end_)
        else:
            self.opf_by_groups()

        self.progress_signal.emit(0.0)
        self.progress_text.emit('Done!')
        self.done_signal.emit()

    def cancel(self):
        self.__cancel__ = True
        self.progress_signal.emit(0.0)
        self.progress_text.emit('Cancelled!')
        self.done_signal.emit()