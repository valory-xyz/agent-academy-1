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

    DEPLOY_DECISION = "deploy_decision"
    DEPLOY_BASKET = "deploy_basket"
    DEPLOY_VAULT = "deploy_vault"
    BASKET_ADDRESSES = "basket_addresses"
    VAULT_ADDRESSES = "vault_addresses"
    PERMISSION_VAULT_FACTORY = "permission_vault_factory"

    def __str__(self) -> str:
        """Get the string value of the transaction type."""
        return self.value


class DeployDecisionPayload(BaseTxPayload):
    """Represent a transaction payload of type 'deploy decision'."""

    transaction_type = TransactionType.DEPLOY_DECISION

    def __init__(self, sender: str, deploy_decision: bool, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param deploy_decision: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._deploy_decision = deploy_decision

    @property
    def deploy_decision(self) -> bool:
        """Get the decision."""
        return self._deploy_decision

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(deploy_decision=self.deploy_decision)


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


class BasketAddressesPayload(BaseTxPayload):
    """Represent a transaction payload of type basket addresses."""

    transaction_type = TransactionType.BASKET_ADDRESSES

    def __init__(self, sender: str, basket_addresses: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param basket_addresses: all the baskets deployed
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._basket_addresses = basket_addresses

    @property
    def basket_addresses(self) -> str:
        """Get the decision."""
        return self._basket_addresses

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(basket_addresses=self.basket_addresses)


class PermissionVaultFactoryPayload(BaseTxPayload):
    """Represent a transaction payload of type vault addresses."""

    transaction_type = TransactionType.PERMISSION_VAULT_FACTORY

    def __init__(self, sender: str, permission_factory: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param permission_factory: all the vaults deployed
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._permission_factory = permission_factory

    @property
    def permission_factory(self) -> str:
        """Get the decision."""
        return self._permission_factory

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(permission_factory=self.permission_factory)


class VaultAddressesPayload(BaseTxPayload):
    """Represent a transaction payload of type vault addresses."""

    transaction_type = TransactionType.VAULT_ADDRESSES

    def __init__(self, sender: str, vault_addresses: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param vault_addresses: all the vaults deployed
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._vault_addresses = vault_addresses

    @property
    def vault_addresses(self) -> str:
        """Get the decision."""
        return self._vault_addresses

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(vault_addresses=self.vault_addresses)


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
