"""
Method implemented from the article:
Online voltage stability assessment for load areas based on the holomorphic embedding method
by Chengxi Liu, Bin Wang, Fengkai Hu, Kai Sun and Claus Leth Bak

Implemented by Santiago Peñate Vera 2018
This implementation computes W[n] for all the buses outside the system matrix leading to better results
"""
import numpy as np
np.set_printoptions(linewidth=32000, suppress=False)
from numpy import zeros, ones, mod, angle, conj, array, c_, r_, linalg, Inf, complex128, double
from numpy.linalg import solve
from scipy.sparse.linalg import factorized
from scipy.sparse import lil_matrix
from scipy.sparse import hstack as hstack_s, vstack as vstack_s
import time
# Set the complex precision to use
complex_type = complex128


def prepare_system_matrices(Ybus, Vbus, bus_idx, pqpv, pq, pv, ref):
    """
    Prepare the system matrices
    :param Ybus:
    :param Vbus:
    :param pqpv:
    :param ref:
    :return:
    """
    n_bus = len(Vbus)
    n_bus2 = 2 * n_bus
    npv = len(pv)
    # ##################################################################################################################
    # Compute the starting voltages
    # ##################################################################################################################

    # System matrix
    A = lil_matrix((n_bus2, n_bus2))  # lil matrices are faster to populate

    # Expanded slack voltages
    Vslack = zeros(n_bus2)

    # Populate A
    for a in pqpv:  # rows
        for ii in range(Ybus.indptr[a], Ybus.indptr[a + 1]):  # columns in sparse format
            b = Ybus.indices[ii]

            A[2 * a + 0, 2 * b + 0] = Ybus[a, b].real
            A[2 * a + 0, 2 * b + 1] = -Ybus[a, b].imag
            A[2 * a + 1, 2 * b + 0] = Ybus[a, b].imag
            A[2 * a + 1, 2 * b + 1] = Ybus[a, b].real

    # set vd elements
    for a in ref:
        A[a * 2, a * 2] = 1.0
        A[a * 2 + 1, a * 2 + 1] = 1.0

        Vslack[a * 2] = Vbus[a].real
        Vslack[a * 2 + 1] = Vbus[a].imag

    # Solve starting point voltages
    Vst_expanded = factorized(A.tocsc())(Vslack)

    # Invert the voltages obtained: Get the complex voltage and voltage inverse vectors
    Vst = Vst_expanded[2 * bus_idx] + 1j * Vst_expanded[2 * bus_idx + 1]
    Wst = 1.0 / Vst

    # ##################################################################################################################
    # Compute the final system matrix
    # ##################################################################################################################

    # System matrices
    B = lil_matrix((n_bus2, npv))
    C = lil_matrix((npv, n_bus2 + npv))

    for i, a in enumerate(pv):
        # "a" is the actual bus index
        # "i" is the number of the pv bus in the pv buses list

        B[2 * a + 0, i + 0] = Wst[a].imag
        B[2 * a + 1, i + 0] = Wst[a].real

        C[i + 0, 2 * a + 0] = Vst[a].real
        C[i + 0, 2 * a + 1] = Vst[a].imag

    Asys = vstack_s([
                    hstack_s([A, B]),
                    C
                    ], format="csc")

    return Asys, Vst, Wst


def calc_W(n, V, W):
    """
    Calculation of the inverse coefficients W.
    @param n: Order of the coefficients
    @param V: Structure of voltage coefficients (Ncoeff x nbus elements)
    @param W: Structure of inverse voltage coefficients (Ncoeff x nbus elements)
    @return: Array of inverse voltage coefficients for the order n
    """

    if n == 0:
        res = 1.0 / conj(V[0, :])
    else:
        l = array(range(n))
        res = -(W[l, :] * V[n - l, :]).sum(axis=0)

        res /= conj(V[0, :])

    return res


def get_rhs(n, V, W, Q, Vbus, Vst, Sbus, Pbus, nsys, nbus2, pv, pq, pvpos):
    """
    Right hand side
    :param n: order of the coefficients
    :param V: Voltage coefficients (order, all buses)
    :param W: Inverse voltage coefficients (order, pv buses)
    :param Q: Reactive power coefficients  (order, pv buses)
    :param Vbus: Initial bus estimate (only used to pick the PV buses set voltage)
    :param Vst: Start voltage due to slack injections
    :param Pbus: Active power injections (all the buses)
    :param nsys: number of rows or cols in the system matrix A
    :param nbus2: two times the number of buses
    :param pv: list of pv indices in the grid
    :param pvpos: array from 0..npv
    :return: right hand side vector to solve the coefficients of order n
    """
    rhs = zeros(nsys)
    m = array(range(1, n), dtype=int)
    # ##################################################################################################################
    # PQ nodes
    # ##################################################################################################################

    f1 = conj(Sbus[pq] * W[:, pq][n - 1, :])
    idx1 = 2 * pq
    rhs[idx1 + 0] = f1.real
    rhs[idx1 + 1] = f1.imag

    # ##################################################################################################################
    # PV nodes
    # ##################################################################################################################
    # Compute convolutions
    QW_convolution = (Q[n - m, :] * W[m, :][:, pv].conjugate()).sum(axis=0)  # only pv nodes
    VV_convolution = (V[m, :][:, pv] * V[n - m, :][:, pv].conjugate()).sum(axis=0)  # only pv nodes

    # compute the formulas
    f2 = Pbus[pv] * W[:, pv][n-1, :] + QW_convolution

    epsilon = -0.5 * VV_convolution
    if n == 1:
        epsilon += 0.5 * (abs(Vbus[pv]) ** 2 - abs(Vst[pv]) ** 2)

    # Assign the values to the right hand side vector
    idx2 = 2 * pv
    idx3 = pvpos + nbus2

    rhs[idx2 + 0] = f2.real
    rhs[idx2 + 1] = f2.imag

    if len(idx3) > 0:
        rhs[idx3] = epsilon.real

    else:

        # No PV nodes
        pass

    return rhs


def assign_solution(x, bus_idx, pvpos, pv, nbus):
    """
    Assign the solution vector to the appropriate coefficients
    :param x: solution vector
    :param bus_idx: array from 0..nbus-1
    :param nbus2: two times the number of buses (integer)
    :param pvpos: array from 0..npv
    :return: Array of:
            - voltage coefficients
            - reactive power
            of order n
    """

    nbus2 = 2 * nbus

    # assign the voltage coefficients
    v = x[2 * bus_idx] + 1j * x[2 * bus_idx + 1]

    if len(pvpos) > 0:

        # assign the reactive power coefficients of the PV nodes
        q = x[nbus2 + pvpos]

    else:

        # No PV nodes

        q = zeros(0)

    return v, q


def pade_approximation(n, an, s=1):
    """
    Computes the n/2 pade approximant of the series an at the approximation
    point s

    Arguments:
        an: coefficient matrix, (number of coefficients, number of series)
        n:  order of the series
        s: point of approximation

    Returns:
        pade approximation at s
    """
    nn = int(n / 2)
    if mod(nn, 2) == 0:
        nn -= 1

    L = nn
    M = nn

    an = np.ndarray.flatten(an)
    rhs = an[L + 1:L + M + 1]

    C = zeros((L, M), dtype=complex_type)
    for i in range(L):
        k = i + 1
        C[i, :] = an[L - M + k:L + k]

    try:
        b = solve(C, -rhs)  # bn to b1
    except:
        return 0, zeros(L + 1, dtype=complex_type), zeros(L + 1, dtype=complex_type)

    b = r_[1, b[::-1]]  # b0 = 1

    a = zeros(L + 1, dtype=complex_type)
    a[0] = an[0]
    for i in range(L):
        val = complex_type(0)
        k = i + 1
        for j in range(k + 1):
            val += an[k - j] * b[j]
        a[i + 1] = val

    p = complex_type(0)
    q = complex_type(0)
    for i in range(L + 1):
        p += a[i] * s ** i
        q += b[i] * s ** i

    return p / q, a, b


def helm(Vbus, Sbus, Ybus, pq, pv, ref, pqpv, tol=1e-9, max_coefficient_count=30):
    """
    Helm Method
    :param Vbus: voltages array
    :param Sbus: Power injections array
    :param Ibus: Currents injection array
    :param Ybus: System admittance matrix
    :param pq: list of pq node indices
    :param pv: list of pv node indices
    :param ref: list of slack node indices
    :param pqpv: list of pq and pv node indices sorted
    :param tol: tolerance
    :return: Voltage array and the power mismatch
    """
    start = time.time()

    nbus = len(Vbus)
    npv = len(pv)
    bus_idx = array(range(nbus), dtype=int)
    pvpos = array(range(npv))

    # Prepare system matrices
    Asys, Vst, Wst = prepare_system_matrices(Ybus, Vbus, bus_idx, pqpv, pq, pv, ref)

    # Factorize the system matrix
    Afact = factorized(Asys)

    # get the shape
    nsys = Asys.shape[0]

    # declare the active power injections
    Pbus = Sbus.real

    # declare the matrix of coefficients: [order, bus index]
    V = zeros((1, nbus), dtype=complex_type)

    # Declare the inverse voltage coefficients: [order, pv bus index]
    W = zeros((1, nbus), dtype=complex_type)

    # Reactive power coefficients on the PV nodes: [order, pv bus index]
    Q = zeros((1, npv), dtype=double)

    # Assign the initial values
    V[0, :] = Vst
    W[0, :] = Wst

    # Compute the reactive power matching the initial solution Vst, then assign it as initial reactive power
    Scalc = Vst * conj(Ybus * Vst)
    Q[0, :] = Scalc[pv].imag

    n = 1
    converged = False

    while n < max_coefficient_count and not converged:

        # Compute the free terms
        rhs = get_rhs(n=n, V=V, W=W, Q=Q,
                      Vbus=Vbus, Vst=Vst,
                      Sbus=Sbus,
                      Pbus=Pbus, nsys=nsys,
                      nbus2=2 * nbus,
                      pv=pv, pq=pq,
                      pvpos=pvpos)

        # Solve the linear system Asys x res = rhs
        res = Afact(rhs)

        # get the new rows of coefficients
        v, q = assign_solution(x=res, bus_idx=bus_idx, pvpos=pvpos, pv=pv, nbus=nbus)

        # Add coefficients row
        V = np.vstack((V, v))
        Q = np.vstack((Q, q))

        # Calculate W[n] and add it to the coefficients structure
        w = calc_W(n, V, W)
        W = np.vstack((W, w))

        voltage = V.sum(axis=0)

        # Calculate the error and check the convergence
        Scalc = voltage * conj(Ybus * voltage)
        mismatch = Scalc - Sbus  # complex power mismatch
        power_mismatch_ = r_[mismatch[pv].real, mismatch[pq].real, mismatch[pq].imag]

        # check for convergence
        normF = linalg.norm(power_mismatch_, Inf)

        converged = normF < tol
        n += 1

    end = time.time()
    elapsed = end - start

    # V, converged, normF, Scalc, it, el
    return voltage, converged, normF, Scalc, n, elapsed


def res_2_df(V, Sbus, tpe):
    """
    Create dataframe to display the results nicely
    :param V: Voltage complex vector
    :param Sbus: Power complex vector
    :param tpe: Types
    :return: Pandas DataFrame
    """
    vm = abs(V)
    va = angle(V)

    d = {1: 'PQ', 2: 'PV', 3: 'VD'}

    tpe_str = array([d[i] for i in tpe], dtype=object)
    data = c_[tpe_str, Sbus.real, Sbus.imag, vm, va]
    cols = ['Type', 'P', 'Q', '|V|', 'angle']
    df = pd.DataFrame(data=data, columns=cols)

    return df


if __name__ == '__main__':
    from GridCal.Engine import *

    file_name = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/IEEE 14.xlsx'

    grid = FileOpen(file_name).open()

    grid.compile()

    circuit = grid.circuits[0]

    print('\nYbus:\n', circuit.power_flow_input.Ybus.todense())
    print('\nSbus:\n', circuit.power_flow_input.Sbus)
    print('\nIbus:\n', circuit.power_flow_input.Ibus)
    print('\nVbus:\n', circuit.power_flow_input.Vbus)
    print('\ntypes:\n', circuit.power_flow_input.types)
    print('\npq:\n', circuit.power_flow_input.pq)
    print('\npv:\n', circuit.power_flow_input.pv)
    print('\nvd:\n', circuit.power_flow_input.ref)

    start_time = time.time()

    v, err = helm(Vbus=circuit.power_flow_input.Vbus,
                  Sbus=circuit.power_flow_input.Sbus,
                  Ibus=circuit.power_flow_input.Ibus,
                  Ybus=circuit.power_flow_input.Ybus,
                  pq=circuit.power_flow_input.pq,
                  pv=circuit.power_flow_input.pv,
                  ref=circuit.power_flow_input.ref,
                  pqpv=circuit.power_flow_input.pqpv)

    print('HEM:')
    print("--- %s seconds ---" % (time.time() - start_time))
    print('Results:\n', res_2_df(v, circuit.power_flow_input.Sbus, circuit.power_flow_input.types))
    print('error: \t', err)

    # check the HELM solution: v against the NR power flow
    print('\nNR')
    options = PowerFlowOptions(SolverType.NR, verbose=False, tolerance=1e-9, control_q=False)
    power_flow = PowerFlow(grid, options)

    start_time = time.time()
    power_flow.run()
    print("--- %s seconds ---" % (time.time() - start_time))
    vnr = circuit.power_flow_results.voltage

    print('Results:\n', res_2_df(vnr, circuit.power_flow_input.Sbus, circuit.power_flow_input.types))
    print('error: \t', circuit.power_flow_results.error)

    # check
    print('\ndiff:\t', v - vnr)