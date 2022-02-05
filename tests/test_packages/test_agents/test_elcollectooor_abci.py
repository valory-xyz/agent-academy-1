# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021 Valory AG
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

from tests.fixture_helpers import UseGanacheFork
from tests.helpers.constants import (
    TARGET_PROJECT_ID as _DEFAULT_TARGET_PROJECT_ID
)

# check log messages of the happy path
from tests.test_packages.test_agents.base import BaseTestElCollectooorEnd2End

TARGET_PROJECT_ID = _DEFAULT_TARGET_PROJECT_ID

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

    "Entered in the 'observation' round for period 0",
    f"Retrieved project with id {TARGET_PROJECT_ID}",
    "'observation' round is done",

    "Entered in the 'details' round for period 0",
    f"Successfully gathered details on project with id={TARGET_PROJECT_ID}.",
    "Total length of details array 1.",
    "'details' round is done",

    "Entered in the 'decision' round",
    f"decided 1 for project with id {TARGET_PROJECT_ID}",
    "'decision' round is done",

    "Entered in the 'transaction_collection' round for period 0",
    "'transaction_collection' round is done",

    "Entered in the 'randomness_transaction_submission' round for period 0",
    "'randomness_transaction_submission' round is done",
    "Entered in the 'select_keeper_transaction_submission_a' round for period 0",
    "'select_keeper_transaction_submission_a' round is done",
    "Entered in the 'collect_signature' round for period 0",
    "Signature:",
    "'collect_signature' round is done",

    "Entered in the 'finalization' round for period 0",
    "'finalization' round is done",
    "Entered in the 'validate_transaction' round for period 0",
    "'validate_transaction' round is done",
    "Period end",
    "Entered in the 'reset_and_pause' round for period 0",
    "'reset_and_pause' round is done",
    "Period end",

    "Entered in the 'randomness_transaction_submission' round for period 1",
    "Entered in the 'select_keeper_transaction_submission_a' round for period 1",
    "Entered in the 'collect_signature' round for period 1",
    "Entered in the 'finalization' round for period 1",
    "Entered in the 'validate_transaction' round for period 1",
    "Entered in the 'reset_and_pause' round for period 1",
)


class TestSingleAgentElCollectooor(
    BaseTestElCollectooorEnd2End,
    UseGanacheFork,
):
    """Test the El Collectooor with only one agent."""

    NB_AGENTS = 1
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS


class TestTwoAgentsElCollectooor(
    BaseTestElCollectooorEnd2End,
    UseGanacheFork,
):
    """Test the El Collectooor with two agents."""

    NB_AGENTS = 2
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS


class TestFourAgentsElCollectooor(
    BaseTestElCollectooorEnd2End,
    UseGanacheFork,
):
    """Test the El Collectooor with four agents."""

    NB_AGENTS = 4
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS
