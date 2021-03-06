"""
Created at 03.2020
"""

import numba
import numpy as np
from MPyDATA.arakawa_c.indexers import indexers, MAX_DIM_NUM


def make_antidiff(non_unit_g_factor, options, traversals):
    if options.n_iters <= 1:
        @numba.njit(**options.jit_flags)
        def apply(_1, _2, _3, _4, _5, _6, _7):
            return
    else:
        idx = indexers[traversals.n_dims]
        apply_vector = traversals.apply_vector()

        formulae_antidiff = tuple([
            __make_antidiff(idx.atv[i], idx.at[i],
                            non_unit_g_factor=non_unit_g_factor,
                            options=options,
                            n_dims=traversals.n_dims)
            if i < traversals.n_dims else None
            for i in range(MAX_DIM_NUM)])

        @numba.njit(**options.jit_flags)
        def apply(GC_corr, psi, psi_bc, GC_unco, vec_bc, g_factor, g_factor_bc):
            return apply_vector(*formulae_antidiff, *GC_corr, *psi, *psi_bc, *GC_unco, *vec_bc,
                                *g_factor, *g_factor_bc)

    return apply


def __make_antidiff(atv, at, non_unit_g_factor, options, n_dims):
    infinite_gauge = options.infinite_gauge
    divergent_flow = options.divergent_flow
    third_order_terms = options.third_order_terms
    epsilon = options.epsilon

    # eq. 13 in Smolarkiewicz 1984; eq. 17a in Smolarkiewicz & Margolin 1998
    @numba.njit(**options.jit_flags)
    def A(psi):
        result = at(*psi, 1, 0) - at(*psi, 0, 0)
        if infinite_gauge:
            result /= 2
        else:
            result /= (at(*psi, 1, 0) + at(*psi, 0, 0) + epsilon)
        return result

    # eq. 13 in Smolarkiewicz 1984; eq. 17b in Smolarkiewicz & Margolin 1998
    @numba.njit(**options.jit_flags)
    def B(psi):
        result = (
                at(*psi, 1, 1) + at(*psi, 0, 1) -
                at(*psi, 1, -1) - at(*psi, 0, -1)
        )
        if infinite_gauge:
            result /= 4
        else:
            result /= (
                    at(*psi, 1, 1) + at(*psi, 0, 1) +
                    at(*psi, 1, -1) + at(*psi, 0, -1) +
                    epsilon
            )
        return result

    @numba.njit(**options.jit_flags)
    def antidiff_basic(psi, GC, _):
        # eq. 13 in Smolarkiewicz 1984
        result = (np.abs(atv(*GC, .5, 0.)) - atv(*GC, +.5, 0.) ** 2) * A(psi)
        if n_dims == 1:
            return result
        else:
            result -= (
                0.5 * atv(*GC, .5, 0.) *
                0.25 * (atv(*GC, 1., +.5) + atv(*GC, 0., +.5) + atv(*GC, 1., -.5) + atv(*GC, 0., -.5)) *
                B(psi)
            )
        return result

    @numba.njit(**options.jit_flags)
    def antidiff_variants(psi, GC, G):
        # eq. 13 in Smolarkiewicz 1984
        result = antidiff_basic(psi, GC, G)

        G_bar = (at(*G, 1, 0) + at(*G, 0, 0)) / 2 if non_unit_g_factor else 1

        # third-order terms
        if third_order_terms:
            # assert psi.dimension < 3  # TODO
            tmp = (
              3 * atv(*GC, .5, 0) * np.abs(atv(*GC, .5, 0)) / G_bar
              - 2 * atv(*GC, .5, 0) ** 3 / G_bar ** 2
              - atv(*GC, .5, 0)
            ) / 6

            tmp *= 2 * (at(*psi, 2, 0) - at(*psi, 1, 0) - at(*psi, 0, 0) + at(*psi, -1, 0))

            if infinite_gauge:
                tmp /= (1 + 1 + 1 + 1)
            else:
                tmp /= at(*psi, 2, 0) + at(*psi, 1, 0) + at(*psi, 0, 0) + at(*psi, -1, 0) + epsilon

            result += tmp

            # if psi.dimension > 1:
            #     GC1_bar = (
            #                       GC.at(1, .5) +
            #                       GC.at(0, .5) +
            #                       GC.at(1, -.5) +
            #                       GC.at(0, -.5)
            #               ) / 4
            #     tmp = GC1_bar / (2 * G_bar) * (
            #             np.abs(GC.at(.5, 0)) - 2 * GC.at(.5, 0) ** 2 / G_bar
            #     )
            #
            #     tmp *= 2 * (psi.at(1, 1) - psi.at(0, 1) - psi.at(1, -1) + psi.at(0, -1))
            #
            #     if infinite_gauge:
            #         tmp /= (1 + 1 + 1 + 1)
            #     else:
            #         tmp /= (psi.at(1, 1) + psi.at(0, 1) + psi.at(1, -1) + psi.at(0, -1))
            #
            #     result += tmp

        # divergent flow option
        # eq.(30) in Smolarkiewicz_and_Margolin_1998
        if divergent_flow:
            # assert psi.dimension == 1  # TODO!
            tmp = -.25 * atv(*GC, .5, 0.) * (atv(*GC, 1.5, 0.) - atv(*GC, -.5, 0.))
            if non_unit_g_factor:
                tmp /= G_bar
            if infinite_gauge:
                tmp *= .5 * at(*psi, 1, 0) + at(*psi, 0, 0)

            result += tmp
        return result
    return antidiff_variants if divergent_flow or third_order_terms else antidiff_basic
