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

"""This module contains the shared state for the 'elcollectooor_abci' application."""

from typing import Any, Optional

from packages.valory.skills.abstract_round_abci.models import ApiSpecs, BaseParams
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from packages.valory.skills.elcollectooor_abci.rounds import ElCollectooorAbciApp, Event


MARGIN = 5

Requests = BaseRequests


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

    def _get_starting_project_id(self, kwargs: dict) -> Optional[int]:
        """Get the value of starting_project_id, or warn and return None"""
        key = "starting_project_id"
        res = kwargs.pop(key)

        try:
            return int(res)
        except TypeError:
            self.context.logger.warning(
                f"'{key}' was not provided, None was used as fallback"
            )
            return None


Params = ElCollectooorParams


class RandomnessApi(ApiSpecs):
    """A model that wraps ApiSpecs for randomness api specifications."""
