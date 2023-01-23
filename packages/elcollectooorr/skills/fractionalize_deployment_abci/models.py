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

"""This module contains the shared state for the 'fractionalize Deployment_abci' application."""

from typing import Any

from packages.valory.skills.abstract_round_abci.models import ApiSpecs, BaseParams
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.transaction_settlement_abci.models import TransactionParams


MARGIN = 5

Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool


class FractionalizeDeploymentParams(BaseParams):
    """Fractionalize Specific Params Class"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the Fractionalize Deployment parameters object.

        :param *args: param args, used only in the superclass
        :param **kwargs: dict with the parameters needed for the Fractionalize Deployment
        """
        self.settings_address = self._ensure("settings_address", kwargs, type_=str)
        self.basket_factory_address = self._ensure("basket_factory_address", kwargs, type_=str)
        self.token_vault_factory_address = self._ensure(
            "token_vault_factory_address", kwargs, type_=str
        )
        self.wei_to_fraction = self._ensure("wei_to_fraction", kwargs, type_=int)
        self.budget_per_vault = self._ensure("budget_per_vault", kwargs, type_=int)
        super().__init__(*args, **kwargs)


class Params(FractionalizeDeploymentParams, TransactionParams):
    """Union class for Fractionalize and Transaction Settlement ABCI"""


class RandomnessApi(ApiSpecs):
    """A model that wraps ApiSpecs for randomness api specifications."""
