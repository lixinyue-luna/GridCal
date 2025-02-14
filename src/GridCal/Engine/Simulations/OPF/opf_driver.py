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
from enum import Enum
import numpy as np
from PySide2.QtCore import QThread, Signal

from GridCal.Engine.basic_structures import TimeGrouping
from GridCal.Engine.Simulations.OPF.opf_results import OptimalPowerFlowResults
from GridCal.Engine.Core.multi_circuit import MultiCircuit
from GridCal.Engine.Simulations.OPF.ac_opf import AcOpf
from GridCal.Engine.Simulations.OPF.dc_opf import DcOpf
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import SolverType
from GridCal.Engine.Simulations.OPF.nelder_mead_opf import AcOpfNelderMead
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import PowerFlowOptions

########################################################################################################################
# Optimal Power flow classes
########################################################################################################################


class OptimalPowerFlowOptions:

    def __init__(self, verbose=False,
                 solver: SolverType = SolverType.DC_OPF,
                 grouping: TimeGrouping = TimeGrouping.NoGrouping,
                 realistic_results=False,
                 faster_less_accurate=False,
                 power_flow_options=None, bus_types=None):
        """

        :param verbose:
        :param solver:
        :param grouping:
        :param realistic_results:
        :param faster_less_accurate:
        :param power_flow_options:
        :param bus_types:
        """
        self.verbose = verbose

        self.solver = solver

        self.grouping = grouping

        self.realistic_results = realistic_results

        self.faster_less_accurate = faster_less_accurate

        self.power_flow_options = power_flow_options

        self.bus_types = bus_types


class OptimalPowerFlow(QThread):
    progress_signal = Signal(float)
    progress_text = Signal(str)
    done_signal = Signal()

    def __init__(self, grid: MultiCircuit, options: OptimalPowerFlowOptions):
        """
        PowerFlow class constructor
        @param grid: MultiCircuit Object
        @param options: OPF options
        """
        QThread.__init__(self)

        # Grid to run a power flow in
        self.grid = grid

        # Options to use
        self.options = options

        # OPF results
        self.results = None

        # set cancel state
        self.__cancel__ = False

        self.all_solved = True

    def get_steps(self):
        """
        Get time steps list of strings
        """
        return list()

    def opf(self):
        """
        Run a power flow for every circuit
        @return: OptimalPowerFlowResults object
        """
        # print('PowerFlow at ', self.grid.name)

        # self.progress_signal.emit(0.0)
        numerical_circuit = self.grid.compile()

        if self.options.solver == SolverType.DC_OPF:
            # DC optimal power flow
            problem = DcOpf(numerical_circuit=numerical_circuit)

        elif self.options.solver == SolverType.AC_OPF:
            # AC optimal power flow
            problem = AcOpf(numerical_circuit=numerical_circuit)
        else:
            raise Exception('Solver not recognized ' + str(self.options.solver))

        # Solve
        problem.solve()

        # get the branch flows (it is used more than one time)
        Sbr = problem.get_branch_power()
        ld = problem.get_load_shedding()
        ld[ld == None] = 0
        bt = problem.get_battery_power()
        bt[bt == None] = 0
        gn = problem.get_generator_power()
        gn[gn == None] = 0

        # pack the results
        self.results = OptimalPowerFlowResults(Sbus=None,
                                               voltage=problem.get_voltage(),
                                               load_shedding=ld * self.grid.Sbase,
                                               generation_shedding=np.zeros_like(ld) * self.grid.Sbase,
                                               battery_power=bt * self.grid.Sbase,
                                               controlled_generation_power=gn * self.grid.Sbase,
                                               Sbranch=Sbr * self.grid.Sbase,
                                               overloads=problem.get_overloads(),
                                               loading=problem.get_loading(),
                                               converged=bool(problem.converged()),
                                               bus_types=numerical_circuit.bus_types)

        return self.results

    def run(self):
        """

        :return:
        """
        self.opf()

        self.progress_text.emit('Done!')
        self.done_signal.emit()

    def cancel(self):
        self.__cancel__ = True

