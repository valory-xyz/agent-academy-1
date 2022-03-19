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

"""This module contains the shared state for the 'elcollectooor_abci' application."""

from typing import Any, Dict, Optional, Type

from packages.valory.skills.abstract_round_abci.models import ApiSpecs, BaseParams
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from packages.valory.skills.elcollectooor_abci.decision_models import (
    BaseDecisionModel,
    GibDetailsThenYesDecisionModel,
    NoDecisionModel,
    SimpleDecisionModel,
    YesDecisionModel,
)
from packages.valory.skills.elcollectooor_abci.rounds import ElCollectooorAbciApp, Event
from packages.valory.skills.transaction_settlement_abci.models import TransactionParams


MARGIN = 5

Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the state."""
        super().__init__(*args, abci_app_cls=ElCollectooorAbciApp, **kwargs)

    def setup(self) -> None:
        """Set up."""
        super().setup()
        ElCollectooorAbciApp.event_to_timeout[
            Event.ROUND_TIMEOUT
        ] = self.context.params.round_timeout_seconds
        ElCollectooorAbciApp.event_to_timeout[Event.RESET_TIMEOUT] = (
            self.context.params.observation_interval + MARGIN
        )


class ElCollectooorParams(BaseParams):
    """El Collectooor Specific Params Class"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the El Collectooor parameters object.

        :param *args: param args, used only in the superclass
        :param **kwargs: dict with the parameters needed for the El Collectooor
        """

        super().__init__(*args, **kwargs)
        self.artblocks_contract = self._ensure("artblocks_contract", kwargs)
        self.artblocks_periphery_contract = self._ensure(
            "artblocks_periphery_contract", kwargs
        )
        self.starting_project_id = self._get_starting_project_id(kwargs)
        self.max_retries = int(kwargs.pop("max_retries", 5))
        self.decision_model_type = self._get_decision_model_type(kwargs)

    def _get_starting_project_id(self, kwargs: dict) -> Optional[int]:
        """Get the value of starting_project_id, or warn and return None"""
        key = "starting_project_id"

        try:
            res = kwargs.pop(key)
            return int(res)
        except TypeError:
            self.context.logger.warning(
                f"'{key}' was not provided, None was used as fallback"
            )
            return None

    def _get_decision_model_type(self, kwargs: dict) -> Type[BaseDecisionModel]:
        """
        Get the decision model type to use

        :param kwargs: provided keyword arguments
        :return: the decision model type
        """

        key = "decision_model_type"
        model_type = kwargs.pop(key, None)
        valid_types: Dict[str, Type[BaseDecisionModel]] = {
            "yes": YesDecisionModel,
            "no": NoDecisionModel,
            "gib_details_then_yes": GibDetailsThenYesDecisionModel,
            "simple": SimpleDecisionModel,
        }

        if not model_type or str(model_type).lower() not in valid_types.keys():
            self.context.logger.warning(
                f"{key} was None or was not in types={valid_types.keys()}, using type 'simple' as the model type"
            )
            model_type = "simple"

        model_type = str(model_type).lower()

        return valid_types[model_type]


class Params(ElCollectooorParams, TransactionParams):
    """Union class for ElCollectoor and Transaction Settlement ABCI"""


class RandomnessApi(ApiSpecs):
    """A model that wraps ApiSpecs for randomness api specifications."""
