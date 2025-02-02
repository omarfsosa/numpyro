# Copyright Contributors to the Pyro project.
# SPDX-License-Identifier: Apache-2.0

from collections import namedtuple

import numpy as np
from numpy.testing import assert_allclose
import pytest

import jax.numpy as jnp

from numpyro.contrib.einstein.kernels import (
    GraphicalKernel,
    HessianPrecondMatrix,
    IMQKernel,
    LinearKernel,
    MixtureKernel,
    PrecondMatrixKernel,
    RandomFeatureKernel,
    RBFKernel,
)

jnp.set_printoptions(precision=100)
T = namedtuple("TestSteinKernel", ["kernel", "particle_info", "loss_fn", "kval"])

PARTICLES_2D = np.array([[1.0, 2.0], [-10.0, 10.0], [7.0, 3.0], [2.0, -1]])

TPARTICLES_2D = (np.array([1.0, 2.0]), np.array([10.0, 5.0]))  # transformed particles

TEST_CASES = [
    T(
        RBFKernel,
        lambda d: {},
        lambda x: x,
        {
            "norm": 0.040711474,
            "vector": np.array([0.056071877, 0.7260586]),
            "matrix": np.array([[0.040711474, 0.0], [0.0, 0.040711474]]),
        },
    ),
    T(RandomFeatureKernel, lambda d: {}, lambda x: x, {"norm": 12.190277}),
    T(
        IMQKernel,
        lambda d: {},
        lambda x: x,
        {"norm": 0.104828484, "vector": np.array([0.11043153, 0.31622776])},
    ),
    T(LinearKernel, lambda d: {}, lambda x: x, {"norm": 21.0}),
    T(
        lambda mode: MixtureKernel(
            mode=mode,
            ws=np.array([0.2, 0.8]),
            kernel_fns=[RBFKernel(mode), RBFKernel(mode)],
        ),
        lambda d: {},
        lambda x: x,
        {"matrix": np.array([[0.040711474, 0.0], [0.0, 0.040711474]])},
    ),
    T(
        lambda mode: GraphicalKernel(
            mode=mode, local_kernel_fns={"p1": RBFKernel("norm")}
        ),
        lambda d: {"p1": (0, d)},
        lambda x: x,
        {"matrix": np.array([[0.040711474, 0.0], [0.0, 0.040711474]])},
    ),
    T(
        lambda mode: PrecondMatrixKernel(
            HessianPrecondMatrix(), RBFKernel(mode="matrix"), precond_mode="const"
        ),
        lambda d: {},
        lambda x: -0.02 / 12 * x[0] ** 4 - 0.5 / 12 * x[1] ** 4 - x[0] * x[1],
        {
            "matrix": np.array(
                [[2.3780507e-04, -1.6688075e-05], [-1.6688075e-05, 1.2849815e-05]]
            )
        },
    ),  # -hess = [[.02x_0^2 1] [1 .5x_1^2]]
]

PARTICLES = [(PARTICLES_2D, TPARTICLES_2D)]

TEST_IDS = [t[0].__class__.__name__ for t in TEST_CASES]


@pytest.mark.parametrize(
    "kernel, particle_info, loss_fn, kval", TEST_CASES, ids=TEST_IDS
)
@pytest.mark.parametrize("particles, tparticles", PARTICLES)
@pytest.mark.parametrize("mode", ["norm", "vector", "matrix"])
def test_kernel_forward(
    kernel, particles, particle_info, loss_fn, tparticles, mode, kval
):
    if mode not in kval:
        return
    (d,) = tparticles[0].shape
    kernel_fn = kernel(mode=mode).compute(particles, particle_info(d), loss_fn)
    value = kernel_fn(*tparticles)

    assert_allclose(value, kval[mode], atol=1e-9)
