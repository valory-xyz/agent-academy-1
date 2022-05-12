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

"""End2end tests base classes for this repo."""

from aea.configurations.base import PublicId

from tests.helpers.constants import ARTBLOCKS_ADDRESS as _DEFAULT_ARTBLOCKS_ADDRESS
from tests.helpers.constants import (
    ARTBLOCKS_PERIPHERY_ADDRESS as _DEFAULT_ARTBLOCKS_PERIPHERY_ADDRESS,
)
from tests.helpers.constants import DECISION_MODEL_TYPE as _DEFAULT_DECISION_MODEL_TYPE
from tests.helpers.constants import TARGET_PROJECT_ID as _DEFAULT_TARGET_PROJECT_ID
from tests.helpers.tendermint_utils import TendermintNodeInfo
from tests.test_agents.base import BaseTestEnd2EndNormalExecution


class BaseTestElCollectooorEnd2End(BaseTestEnd2EndNormalExecution):
    """
    Extended base class for conducting E2E tests with the El Collectooor.

    Test subclasses must set NB_AGENTS, agent_package, wait_to_finish and check_strings.
    """

    STARTING_PROJECT_ID = _DEFAULT_TARGET_PROJECT_ID + 1
    ARTBLOCKS_ADDRESS = _DEFAULT_ARTBLOCKS_ADDRESS
    ARTBLOCKS_PERIPHERY_ADDRESS = _DEFAULT_ARTBLOCKS_PERIPHERY_ADDRESS
    DECISION_MODEL_TYPE = _DEFAULT_DECISION_MODEL_TYPE

    def __set_configs(self, node: TendermintNodeInfo) -> None:
        """Set the current agent's config overrides."""
        super().__set_configs(node)
        self.set_config(
            f"vendor.valory.skills.{PublicId.from_str(self.skill_package).name}.models.params.args.starting_project_id",
            self.STARTING_PROJECT_ID,
        )
        self.set_config(
            f"vendor.valory.skills.{PublicId.from_str(self.skill_package).name}.models.params.args.artblocks_contract",
            self.ARTBLOCKS_ADDRESS,
        )
        self.set_config(
            f"vendor.valory.skills.{PublicId.from_str(self.skill_package).name}.models.params.args.artblocks_periphery_contract",
            self.ARTBLOCKS_PERIPHERY_ADDRESS,
        )
        self.set_config(
            f"vendor.valory.skills.{PublicId.from_str(self.skill_package).name}.models.params.args.artblocks_periphery_contract",
            self.ARTBLOCKS_PERIPHERY_ADDRESS,
        )
        self.set_config(
            f"vendor.valory.skills.{PublicId.from_str(self.skill_package).name}.models.params.args.decision_model_type",
            self.DECISION_MODEL_TYPE,
        )
