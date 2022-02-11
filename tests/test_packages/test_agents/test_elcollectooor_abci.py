# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2022 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Integration tests for the valory/price_estimation_abci skill."""

import pytest

from tests.fixture_helpers import UseGnosisSafeHardHatNet
from tests.test_packages.test_agents.base import BaseTestEnd2EndNormalExecution


# check log messages of the happy path
CHECK_STRINGS = (
    "Entered in the 'tendermint_healthcheck' behaviour state",
    "'tendermint_healthcheck' behaviour state is done",
    "Entered in the 'registration_startup' round for period 0",
    "'registration_startup' round is done",
    "Entered in the 'randomness_safe' round for period 0",
    "'randomness_safe' round is done",
    "Entered in the 'select_keeper_safe' round for period 0",
    "'select_keeper_safe' round is done",
    "Entered in the 'deploy_safe' round for period 0",
    "'deploy_safe' round is done",
    "Entered in the 'validate_safe' round for period 0",
    "'validate_safe' round is done",
    "TBD",
    "Entered in the 'randomness_transaction_submission' round for period 0",
    "'randomness_transaction_submission' round is done",
    "Entered in the 'select_keeper_transaction_submission_a' round for period 0",
    "'select_keeper_transaction_submission_a' round is done",
    "Entered in the 'collect_signature' round for period 0",
    "Signature:",
    "'collect_signature' round is done",
    "Entered in the 'finalization' round for period 0",
    "'finalization' round is done",
    "Finalized estimate",
    "Entered in the 'validate_transaction' round for period 0",
    "'validate_transaction' round is done",
    "Period end",
    "Entered in the 'reset_and_pause' round for period 0",
    "'reset_and_pause' round is done",
    "Period end",
    "TBD",
    "Entered in the 'randomness_transaction_submission' round for period 1",
    "Entered in the 'select_keeper_transaction_submission_a' round for period 1",
    "Entered in the 'collect_signature' round for period 1",
    "Entered in the 'finalization' round for period 1",
    "Entered in the 'validate_transaction' round for period 1",
    "Entered in the 'reset_and_pause' round for period 1",
)


@pytest.mark.e2e
class TestABCIPriceEstimationSingleAgent(
    BaseTestEnd2EndNormalExecution,
    UseGnosisSafeHardHatNet,
):
    """Test that the ABCI price_estimation skill with only one agent."""

    NB_AGENTS = 1
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS


@pytest.mark.e2e
class TestABCIPriceEstimationTwoAgents(
    BaseTestEnd2EndNormalExecution,
    UseGnosisSafeHardHatNet,
):
    """Test that the ABCI price_estimation skill with two agents."""

    NB_AGENTS = 2
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS


@pytest.mark.e2e
class TestABCIPriceEstimationFourAgents(
    BaseTestEnd2EndNormalExecution,
    UseGnosisSafeHardHatNet,
):
    """Test that the ABCI price_estimation skill with four agents."""

    NB_AGENTS = 4
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS
