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

"""This module contains the transaction payloads for the fractionalize Deployment_abci app."""
from enum import Enum
from typing import Any, Dict

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


class TransactionType(Enum):
    """Enumeration of transaction types."""

    DEPLOY_BASKET = 'deploy_basket'
    DEPLOY_VAULT = 'deploy_vault'

    def __str__(self) -> str:
        """Get the string value of the transaction type."""
        return self.value


class DeployBasketPayload(BaseTxPayload):
    """Represent a transaction payload of type 'deploy basket'."""

    transaction_type = TransactionType.DEPLOY_BASKET

    def __init__(self, sender: str, deploy_basket: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param deploy_basket: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._deploy_basket = deploy_basket

    @property
    def deploy_basket(self) -> str:
        """Get the decision."""
        return self._deploy_basket

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(deploy_basket=self.deploy_basket)

class DeployVaultPayload(BaseTxPayload):
    """Represent a transaction payload of type 'deploy vault'."""

    transaction_type = TransactionType.DEPLOY_VAULT

    def __init__(self, sender: str, deploy_vault: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param deploy_vault: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._deploy_vault = deploy_vault

    @property
    def deploy_vault(self) -> str:
        """Get the decision."""
        return self._deploy_vault

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(deploy_vault=self.deploy_vault)
