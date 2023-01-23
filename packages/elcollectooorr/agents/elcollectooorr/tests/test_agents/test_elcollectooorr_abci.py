# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2023 Valory AG
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
# pylint: skip-file
# mypy: ignore-errors
# flake8: noqa

"""Integration tests for the valory/price_estimation_abci skill."""

import pytest
from aea_test_autonomy.fixture_helpers import ipfs_daemon, ipfs_domain  # noqa: F401

from packages.elcollectooorr.agents.elcollectooorr.tests.fixture_helpers import (
    UseHardHatElColBaseTest,
)
from packages.elcollectooorr.agents.elcollectooorr.tests.helpers.constants import (
    TARGET_PROJECT_ID as _DEFAULT_TARGET_PROJECT_ID,
)
from packages.elcollectooorr.agents.elcollectooorr.tests.test_agents.base_elcollectooorr import (
    BaseTestElCollectooorrEnd2End,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.rounds import (
    DecisionRound,
    DetailsRound,
    FundingRound,
    ObservationRound,
    PayoutFractionsRound,
    PostTransactionSettlementRound,
    ProcessPurchaseRound,
    TransactionRound,
    TransferNFTRound,
)
from packages.elcollectooorr.skills.fractionalize_deployment_abci.rounds import (
    BasketAddressRound,
    DeployBasketTxRound,
    DeployDecisionRound,
    PermissionVaultFactoryRound,
    VaultAddressRound,
)
from packages.valory.skills.registration_abci.rounds import RegistrationStartupRound
from packages.valory.skills.reset_pause_abci.rounds import ResetAndPauseRound


TARGET_PROJECT_ID = _DEFAULT_TARGET_PROJECT_ID

REGISTRATION_CHECK_STRINGS = (
    f"Entered in the '{RegistrationStartupRound.auto_round_id()}' round for period 0",
    f"'{RegistrationStartupRound.auto_round_id()}' round is done",
)

BASE_ELCOLLECTOOORR_CHECK_STRINGS = (
    f"Entered in the '{ObservationRound.auto_round_id()}' round for period 0",
    "Most recent project is 3.",
    "There are 2 newly finished projects.",
    "There are 1 active projects.",
    f"'{ObservationRound.auto_round_id()}' round is done with event: Event.DONE",
    f"Entered in the '{DetailsRound.auto_round_id()}' round for period 0",
    f"'{DetailsRound.auto_round_id()}' round is done with event: Event.DONE",
    f"Entered in the '{DecisionRound.auto_round_id()}' round for period 0",
    "The safe contract balance is 1.0Ξ.",
    "The current budget is 1.0Ξ.",
    "1 projects fit the reqs.",
    f"'{DecisionRound.auto_round_id()}' round is done with event: Event.DECIDED_YES",
)

POST_TX_SETTLEMENT_STRINGS = (
    f"Entered in the '{PostTransactionSettlementRound.auto_round_id()}' round for period 0",
    f"The TX submitted by {TransactionRound.auto_round_id()} was settled.",
    f"'{PostTransactionSettlementRound.auto_round_id()}' round is done with event: PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE",
    f"'{PostTransactionSettlementRound.auto_round_id()}' round is done with event: PostTransactionSettlementEvent.TRANSFER_NFT_DONE",
    f"'{PostTransactionSettlementRound.auto_round_id()}' round is done with event: PostTransactionSettlementEvent.BASKET_DONE",
    f"'{PostTransactionSettlementRound.auto_round_id()}' round is done with event: PostTransactionSettlementEvent.VAULT_DONE",
)

FRACTIONALIZE_STRINGS = (
    f"Entered in the '{DeployDecisionRound.auto_round_id()}' round for period 0",
    "Deploy new basket and vault? deploy_full.",
    "Deploy new basket and vault? dont_deploy.",
    f"Entered in the '{DeployBasketTxRound.auto_round_id()}' round for period 0",
    f"'{DeployBasketTxRound.auto_round_id()}' round is done with event: Event.DONE",
    f"Entered in the '{BasketAddressRound.auto_round_id()}' round for period 0",
    "New basket address=0x",
    f"'{BasketAddressRound.auto_round_id()}' round is done with event: Event.DONE",
    f"Entered in the '{PermissionVaultFactoryRound.auto_round_id()}' round for period 0",
    f"'{PermissionVaultFactoryRound.auto_round_id()}' round is done with event: Event.DECIDED_YES",
    "Deployed new TokenVault at: 0x",
    f"'{VaultAddressRound.auto_round_id()}' round is done with event: Event.DONE",
    f"Entered in the '{FundingRound.auto_round_id()}' round for period 0",
    f"'{FundingRound.auto_round_id()}' round is done with event: Event.DONE",
    "1 user(s) is(are) getting paid their fractions.",
    "The following users were paid: {'0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0': 95}",
    f"'{PayoutFractionsRound.auto_round_id()}' round is done with event: Event.DONE",
)

PURCHASE_TOKEN_STRING = (
    f"Entered in the '{ProcessPurchaseRound.auto_round_id()}' round for period 0",
    "Purchased token id=3000000.",
    f"'{ProcessPurchaseRound.auto_round_id()}' round is done with event: Event.DONE",
    f"Entered in the '{TransferNFTRound.auto_round_id()}' round for period 0",
    f"'{TransferNFTRound.auto_round_id()}' round is done with event: Event.DONE",
)

RESET_STRINGS = (
    f"Entered in the '{ResetAndPauseRound.auto_round_id()}' round for period 0",
    "Period end.",
)


@pytest.mark.parametrize("nb_nodes", (4,))
class TestHappyPath(
    BaseTestElCollectooorrEnd2End,
    UseHardHatElColBaseTest,
):
    """Test the El Collectooorr that decides for yes on the target project, and goes through the whole flow."""

    agent_package = "elcollectooorr/elcollectooorr:0.1.0"
    skill_package = "elcollectooorr/elcollectooorr_abci:0.1.0"
    wait_to_finish = 300  # 5 min to complete
    strict_check_strings = (
        REGISTRATION_CHECK_STRINGS
        + BASE_ELCOLLECTOOORR_CHECK_STRINGS
        + POST_TX_SETTLEMENT_STRINGS
        + FRACTIONALIZE_STRINGS
        + PURCHASE_TOKEN_STRING
        + RESET_STRINGS
    )
    use_benchmarks = True
