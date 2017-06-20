from __future__ import division

from numpy.testing import assert_equal, assert_allclose

from pytest import raises, fixture

import numpy as np

from SALib.sample.morris import sample, _compute_optimised_trajectories, \
    generate_p_star, \
    compute_b_star, \
    compute_delta, \
    generate_trajectory
from SALib.util import read_param_file, compute_groups_matrix


@fixture(scope='function')
def setup_input():
    input_1 = [[0, 1 / 3.], [0, 1.], [2 / 3., 1.]]
    input_2 = [[0, 1 / 3.], [2 / 3., 1 / 3.], [2 / 3., 1.]]
    input_3 = [[2 / 3., 0], [2 / 3., 2 / 3.], [0, 2 / 3.]]
    input_4 = [[1 / 3., 1.], [1., 1.], [1, 1 / 3.]]
    input_5 = [[1 / 3., 1.], [1 / 3., 1 / 3.], [1, 1 / 3.]]
    input_6 = [[1 / 3., 2 / 3.], [1 / 3., 0], [1., 0]]
    input_sample = np.concatenate([input_1, input_2, input_3,
                                   input_4, input_5, input_6])
    return input_sample


@fixture(scope='function')
def expected_sample():
    input_1 = [[0, 1 / 3.], [0, 1.], [2 / 3., 1.]]
    input_3 = [[2 / 3., 0], [2 / 3., 2 / 3.], [0, 2 / 3.]]
    input_4 = [[1 / 3., 1.], [1., 1.], [1, 1 / 3.]]
    input_6 = [[1 / 3., 2 / 3.], [1 / 3., 0], [1., 0]]
    return np.concatenate([input_1, input_3, input_4, input_6])


def test_group_in_param_file_read(setup_param_file_with_groups):
    '''
    Tests that groups in a parameter file are read correctly
    '''
    parameter_file = setup_param_file_with_groups
    problem = read_param_file(parameter_file)
    groups, group_names = compute_groups_matrix(
        problem['groups'], problem['num_vars'])

    assert_equal(problem['names'], ["Test 1", "Test 2", "Test 3"])
    assert_equal(groups, np.matrix('1,0;1,0;0,1', dtype=np.int))
    assert_equal(group_names, ['Group 1', 'Group 2'])


def test_grid_jump_lt_num_levels(setup_param_file):

    parameter_file = setup_param_file
    problem = read_param_file(parameter_file)

    samples = 10
    num_levels = 4
    grid_jump = 4

    with raises(ValueError):
        sample(problem, samples, num_levels, grid_jump,
               optimal_trajectories=samples)


def test_optimal_trajectories_lt_samples(setup_param_file):

    parameter_file = setup_param_file
    problem = read_param_file(parameter_file)

    samples = 10
    num_levels = 4
    grid_jump = 2

    with raises(ValueError):
        sample(problem, samples, num_levels, grid_jump,
               optimal_trajectories=samples)


def test_optimal_trajectories_lt_10(setup_param_file):

    parameter_file = setup_param_file
    problem = read_param_file(parameter_file)

    samples = 10
    num_levels = 4
    grid_jump = 2
    optimal_trajectories = 11
    with raises(ValueError):
        sample(problem, samples, num_levels, grid_jump,
               optimal_trajectories=optimal_trajectories)


def test_optimal_trajectories_gte_one(setup_param_file):

    parameter_file = setup_param_file
    problem = read_param_file(parameter_file)

    samples = 10
    num_levels = 4
    grid_jump = 2
    optimal_trajectories = 1

    with raises(ValueError):
        sample(problem, samples, num_levels, grid_jump,
               optimal_trajectories=optimal_trajectories)


def test_find_optimum_trajectories(setup_input, expected_sample):

    N = 6
    problem = {'num_vars': 2, 'groups': None}
    k_choices = 4

    output = _compute_optimised_trajectories(
        problem, setup_input, N, k_choices)
    expected = expected_sample
    np.testing.assert_equal(output, expected)


def test_catch_inputs_not_in_zero_one_range(setup_input):
    problem = {'num_vars': 2, 'groups': None}
    k_choices = 4
    N = 10
    with raises(ValueError):
        _compute_optimised_trajectories(problem, setup_input * 10, N,
                                        k_choices)


def test_group_sample_fails_with_wrong_G_matrix():
    N = 6
    num_levels = 4
    grid_jump = 2
    problem = {'bounds': [[0., 1.], [0., 1.], [0., 1.], [0., 1.]],
               'num_vars': 4,
               'groups': (list([1, 2, 3, 4]), None)}
    with raises(TypeError):
        sample(problem, N, num_levels, grid_jump)


class TestGroupSampleGeneration:

    def test_generate_p_star(self):
        '''
        Matrix P* - size (g * g) - describes order in which groups move
        each row contains one element equal to 1, all others are 0
        no two columns have 1s in the same position
        '''
        for i in range(1, 100):
            output = generate_p_star(i)
            if np.any(np.sum(output, 0) != np.ones(i)):
                raise AssertionError("Not legal P along axis 0")
            elif np.any(np.sum(output, 1) != np.ones(i)):
                raise AssertionError("Not legal P along axis 1")

    def test_compute_delta(self):
        fixture = np.arange(2, 10)
        output = [compute_delta(f) for f in fixture]
        desired = np.array([1.0, 0.75, 0.666667, 0.625,
                            0.6, 0.583333, 0.571429, 0.5625])
        assert_allclose(output, desired, rtol=1e-2)

    def test_generate_trajectory(self):
        # Two groups of three factors
        G = np.array([[1, 0], [0, 1], [0, 1]])
        # Four levels, grid_jump = 2
        num_levels, grid_jump = 4, 2
        output = generate_trajectory(G, num_levels, grid_jump)
        if np.any((output > 1) | (output < 0)):
            raise AssertionError("Bound not working")
        assert_equal(output.shape[0], 3)
        assert_equal(output.shape[1], 3)

    def test_compute_B_star(self):
        '''
        Tests for expected output

        Taken from example 3.2 in Saltelli et al. (2008) pg 122
        '''

        k = 3
        g = 2

        x_star = np.matrix(np.array([1. / 3, 1. / 3, 0.]))
        J = np.matrix(np.ones((g + 1, k)))
        G = np.matrix('1,0;0,1;0,1')
        D_star = np.matrix('1,0,0;0,-1,0;0,0,1')
        P_star = np.matrix('1,0;0,1')
        delta = 2. / 3
        B = np.matrix(np.tril(np.ones([g + 1, g], dtype=int), -1))

        desired = np.array([[1. / 3, 1, 0], [1, 1, 0], [1, 1. / 3, 2. / 3]])

        output = compute_b_star(J, x_star, delta, B, G, P_star, D_star)
        assert_allclose(output, desired)
