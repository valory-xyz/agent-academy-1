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

from tests.fixture_helpers import UseHardHatElColBaseTest
from tests.helpers.constants import TARGET_PROJECT_ID as _DEFAULT_TARGET_PROJECT_ID
from tests.test_agents.base_elcollectooorr import BaseTestElCollectooorrEnd2End


TARGET_PROJECT_ID = _DEFAULT_TARGET_PROJECT_ID

REGISTRATION_CHECK_STRINGS = (
    "Entered in the 'registration_startup' round for period 0",
    "'registration_startup' round is done",
)

SAFE_CHECK_STRINGS = (
    "Entered in the 'randomness_safe' round for period 0",
    "'randomness_safe' round is done",
    "Entered in the 'select_keeper_safe' round for period 0",
    "'select_keeper_safe' round is done",
    "Entered in the 'deploy_safe' round for period 0",
    "'deploy_safe' round is done",
    "Entered in the 'validate_safe' round for period 0",
    "'validate_safe' round is done",
)

BASE_ELCOLLECTOOORR_CHECK_STRINGS = (
    "Entered in the 'observation' round for period 0",
    "Most recent project is 3.",
    "There are 2 newly finished projects.",
    "There are 1 active projects.",
    "'observation' round is done with event: Event.DONE",
    "Entered in the 'details' round for period 0",
    "'details' round is done with event: Event.DONE",
    "Entered in the 'decision' round for period 0",
    "The safe contract balance is 1.0Ξ.",
    "The current budget is 1.0Ξ.",
    "1 projects fit the reqs.",
    "'decision' round is done with event: Event.DECIDED_YES",
)

POST_TX_SETTLEMENT_STRINGS = (
    "Entered in the 'post_transaction_settlement_round' round for period 0",
    "The TX submitted by elcollectooorr_transaction_collection was settled.",
    "'post_transaction_settlement_round' round is done with event: PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE",
    "'post_transaction_settlement_round' round is done with event: PostTransactionSettlementEvent.TRANSFER_NFT_DONE",
    "'post_transaction_settlement_round' round is done with event: PostTransactionSettlementEvent.BASKET_DONE",
    "'post_transaction_settlement_round' round is done with event: PostTransactionSettlementEvent.VAULT_DONE",
)

FRACTIONALIZE_STRINGS = (
    "Entered in the 'deploy_decision_round' round for period 0",
    "Deploy new basket and vault? deploy_full.",
    "Deploy new basket and vault? dont_deploy.",
    "Entered in the 'deploy_basket_round' round for period 0",
    "'deploy_basket_round' round is done with event: Event.DONE",
    "Entered in the 'post_deploy_basket_round' round for period 0",
    "New basket address=0x",
    "'post_deploy_basket_round' round is done with event: Event.DONE",
    "Entered in the 'permission_factory_round' round for period 0",
    "'permission_factory_round' round is done with event: Event.DECIDED_YES",
    "Deployed new TokenVault at: 0x",
    "'post_deploy_vault_round' round is done with event: Event.DONE",
    "Entered in the 'funding_round' round for period 0",
    "'funding_round' round is done with event: Event.DONE",
    "1 user(s) is(are) getting paid their fractions.",
    "The following users were paid: {'0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0': 95}",
    "'payout_fractions_round' round is done with event: Event.DONE",
)

PURCHASE_TOKEN_STRING = (
    "Entered in the 'process_purchase_round' round for period 0",
    "Purchased token id=3000000.",
    "'process_purchase_round' round is done with event: Event.DONE",
    "Entered in the 'transfer_nft_round' round for period 0",
    "'transfer_nft_round' round is done with event: Event.DONE",
)


class TestHappyPath(
    BaseTestElCollectooorrEnd2End,
    UseHardHatElColBaseTest,
):
    """Test the El Collectooorr that decides for yes on the target project, and goes through the whole flow."""

    NB_AGENTS = 4
    agent_package = "valory/elcollectooorr:0.1.0"
    skill_package = "valory/elcollectooorr_abci:0.1.0"
    wait_to_finish = 300  # 5 min to complete
    strict_check_strings = (
        REGISTRATION_CHECK_STRINGS
        + SAFE_CHECK_STRINGS
        + BASE_ELCOLLECTOOORR_CHECK_STRINGS
        + POST_TX_SETTLEMENT_STRINGS
        + FRACTIONALIZE_STRINGS
        + PURCHASE_TOKEN_STRING
    )
    use_benchmarks = True
