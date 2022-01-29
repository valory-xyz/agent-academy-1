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

    "Entered in the 'observation' round for period 0",
    "Retrieved project id: 56",
    "'observation' round is done",

    "Entered in the 'details' round for period 0",
    "Successfully gathered details on project with id=56.",
    "Total length of details array 1.",
    "'details' round is done",

    "Entered in the 'decision' round",
    "decided 1 for project with id 56",
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
    "Finalized estimate",
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


class TestABCIPriceEstimationSingleAgent(
    BaseTestEnd2EndNormalExecution,
):
    """Test that the ABCI price_estimation skill with only one agent."""

    NB_AGENTS = 1
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS
    key_pairs = (("agent1", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d",),)


class TestABCIPriceEstimationTwoAgents(
    BaseTestEnd2EndNormalExecution,
):
    """Test that the ABCI price_estimation skill with two agents."""

    NB_AGENTS = 2
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS
    key_pairs = (
        ("agent1", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"),
        ("agent2", "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1")
    )


class TestABCIPriceEstimationFourAgents(
    BaseTestEnd2EndNormalExecution,
):
    """Test that the ABCI price_estimation skill with four agents."""

    NB_AGENTS = 4
    agent_package = "valory/elcollectooor:0.1.0"
    skill_package = "valory/elcollectooor_abci:0.1.0"
    wait_to_finish = 120
    check_strings = CHECK_STRINGS
    key_pairs = (
        ("agent1", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"),
        ("agent2", "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1"),
        ("agent3", "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c"),
        ("agent4", "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913")
    )
