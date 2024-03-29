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
"""Tests for valory/token_vault_factory contract."""
import time
from typing import Any, Dict, cast

from aea.crypto.registries import crypto_registry
from aea_ledger_ethereum import EthereumCrypto
from aea_test_autonomy.base_test_classes.contracts import (
    BaseGanacheContractWithDependencyTest,
)
from aea_test_autonomy.configurations import ETHEREUM_KEY_PATH_1
from aea_test_autonomy.docker.base import skip_docker_tests

from packages.elcollectooorr.contracts.basket.contract import BasketContract
from packages.elcollectooorr.contracts.basket.tests import PACKAGE_DIR as BASKET_DIR
from packages.elcollectooorr.contracts.basket_factory.contract import (
    BasketFactoryContract,
)
from packages.elcollectooorr.contracts.basket_factory.tests import (
    PACKAGE_DIR as BASKET_FACTORY_DIR,
)
from packages.elcollectooorr.contracts.token_settings.tests import (
    PACKAGE_DIR as TOKEN_SETTINGS_DIR,
)
from packages.elcollectooorr.contracts.token_vault_factory import (
    PACKAGE_DIR as TOKEN_VAULT_FACTORY_DIR,
)
from packages.elcollectooorr.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)


DEFAULT_GAS = 1000000000
DEFAULT_MAX_FEE_PER_GAS = 10 ** 10
DEFAULT_MAX_PRIORITY_FEE_PER_GAS = 10 ** 10


@skip_docker_tests
class BaseTestTokenVaultFactory(BaseGanacheContractWithDependencyTest):  # pylint disable=too-few-public-methods
    """Test deployment of Token Vault Factory to Ganache."""

    contract_directory = TOKEN_VAULT_FACTORY_DIR
    contract: TokenVaultFactoryContract

    dependencies = [
        (
            "token_settings",
            TOKEN_SETTINGS_DIR,
            dict(
                gas=DEFAULT_GAS,
            ),
        )
    ]

    @classmethod
    def deployment_kwargs(cls) -> Dict[str, Any]:
        """Get deployment kwargs."""
        assert (
            cls.dependency_info["token_settings"] is not None
        ), "token_settings is not ready"

        settings_address, _ = cls.dependency_info["token_settings"]

        return dict(
            gas=DEFAULT_GAS,
            _settings=settings_address,
        )


@skip_docker_tests
class TestMainTokenVaultFactory(BaseTestTokenVaultFactory):
    """Test all the functionalities - renounceOwnership"""

    def test_verify(self) -> None:
        """Test verification of deployed contract results."""
        assert self.contract_address is not None
        settings_address, _ = self.dependency_info["token_settings"]

        result = self.contract.verify_contract(
            ledger_api=self.ledger_api,
            contract_address=self.contract_address,
            settings_address=settings_address,
        )
        assert result["verified"], "The bytecode was incorrect."

    def test_pause_unpause(self) -> None:
        """Test that the owner can pause/unpause the contract"""

        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        raw_tx = self.contract.pause(
            self.ledger_api,
            str(self.contract_address),
            self.deployer_crypto.address,
            gas=DEFAULT_GAS,
        )
        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        is_paused = contract.functions.paused().call()

        assert is_paused, "The contract should be paused"

        raw_tx = self.contract.unpause(
            self.ledger_api,
            str(self.contract_address),
            str(self.deployer_crypto.address),
            gas=DEFAULT_GAS,
        )
        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        is_paused = contract.functions.paused().call()

        assert not is_paused, "The contract should not be paused"

    def test_transfer_ownership(self) -> None:
        """Test that the owner can transfer the ownership"""

        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )
        new_owner = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_1
        )

        raw_tx = self.contract.transfer_ownership(
            self.ledger_api,
            str(self.contract_address),
            self.deployer_crypto.address,
            new_owner.address,
            gas=DEFAULT_GAS,
        )
        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        current_owner = contract.functions.owner().call()

        assert current_owner == new_owner.address, "The owner should have been changed"

        # revert ownership ot the old owner so that the other tests are not affected
        raw_tx = self.contract.transfer_ownership(
            self.ledger_api,
            str(self.contract_address),
            new_owner.address,
            self.deployer_crypto.address,
            gas=DEFAULT_GAS,
        )
        tx_signed = new_owner.sign_transaction(raw_tx)
        self.ledger_api.send_signed_transaction(tx_signed)

        time.sleep(3)  # give 3 seconds for the transaction to go through

    def test_get_owner(self) -> None:
        """Test that get_owner returns the owner"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_owner(
            self.ledger_api,
            str(self.contract_address),
        )

        expected_value = contract.functions.owner().call()

        assert actual_value == expected_value, "wrong owner was returned"

    def test_is_paused(self) -> None:
        """Test that is_paused returns the correct value"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.is_paused(
            self.ledger_api,
            str(self.contract_address),
        )

        expected_value = contract.functions.paused().call()

        assert actual_value == expected_value, "is_paused returned the wrong value"

    def test_get_logic(self) -> None:
        """Test that get_logic returns the correct value"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_logic(
            self.ledger_api,
            str(self.contract_address),
        )

        expected_value = contract.functions.logic().call()

        assert actual_value == expected_value, "get_logic returned the wrong value"

    def test_get_settings(self) -> None:
        """Test that get_settings returns the correct value"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_settings_address(
            self.ledger_api,
            str(self.contract_address),
        )

        expected_value = contract.functions.settings().call()

        assert (
            actual_value == expected_value
        ), "get_settings_address returned the wrong value"

    def test_get_vault_count(self) -> None:
        """Test that get_vault_count returns the correct value"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_vault_count(
            self.ledger_api,
            str(self.contract_address),
        )

        expected_value = contract.functions.vaultCount().call()

        assert (
            actual_value == expected_value
        ), "get_vault_count returned the wrong value"

    def test_get_vault(self) -> None:
        """Test that get_vault returns the correct value"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_vault(
            self.ledger_api,
            str(self.contract_address),
            0,
        )

        expected_value = contract.functions.vaults(0).call()

        assert actual_value == expected_value, "get_vault returned the wrong value"


@skip_docker_tests
class TestRenounceTokenVaultFactory(BaseTestTokenVaultFactory):
    """Test renounce ownership"""

    def test_renounce_ownership(self) -> None:
        """Test that the owner can renounce the ownership"""
        contract = TokenVaultFactoryContract.get_instance(
            self.ledger_api, self.contract_address
        )

        raw_tx = self.contract.renounce_ownership(
            self.ledger_api,
            str(self.contract_address),
            self.deployer_crypto.address,
            gas=DEFAULT_GAS,
        )
        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        current_owner = contract.functions.owner().call()

        assert (
            current_owner == "0x0000000000000000000000000000000000000000"
        ), "Couldn't renounce ownership"


@skip_docker_tests
class TestMintTokenVault(BaseTestTokenVaultFactory):
    """Test minting a new token vault"""

    dependencies = BaseTestTokenVaultFactory.dependencies + [
        (
            "basket_factory",
            BASKET_FACTORY_DIR,
            dict(
                gas=DEFAULT_GAS,
            ),
        ),
        (
            "basket",
            BASKET_DIR,
            dict(
                gas=DEFAULT_GAS,
                is_basket=True,
            ),
        ),
    ]

    @classmethod
    def _setup_class(cls, **kwargs: Any) -> None:  # pylint: disable=inconsistent-return-statements
        """Setup class, approve token vault to use the basket"""

        super()._setup_class(**kwargs)

        basket_address, basket_contract = cls.dependency_info["basket"]
        basket_contract = cast(BasketContract, basket_contract)
        raw_tx = basket_contract.set_approve_for_all(
            ledger_api=cls.ledger_api,
            contract_address=basket_address,
            sender_address=cls.deployer_crypto.address,
            operator_address=str(cls.contract_address),
            is_approved=True,
            gas=DEFAULT_GAS,
        )
        if raw_tx is None:
            return None
        tx_signed = cls.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = cls.ledger_api.send_signed_transaction(tx_signed)

        time.sleep(3)  # wait for the transaction to settle

        assert tx_hash is not None, "Tx hash is none"

    @classmethod
    def deploy(cls, **kwargs: Any) -> None:  # pylint: disable=inconsistent-return-statements
        """Deploy the contract."""

        is_basket = kwargs.pop("is_basket", False)

        if not is_basket:
            super().deploy(**kwargs)
            return

        basket_factory_address, _ = cls.dependency_info["basket_factory"]

        tx = cls.contract.get_deploy_transaction(
            ledger_api=cls.ledger_api,
            deployer_address=str(cls.deployer_crypto.address),
            basket_factory_address=basket_factory_address,
            **kwargs,
        )
        if tx is None:
            return None
        tx_signed = cls.deployer_crypto.sign_transaction(tx)
        tx_hash = cls.ledger_api.send_signed_transaction(tx_signed)

        time.sleep(3)  # wait for the transaction to settle

        basket_info = cast(
            Dict,
            BasketFactoryContract.get_basket_address(
                cls.ledger_api,
                basket_factory_address,
                str(tx_hash),
            ),
        )
        cls.contract_address = str(basket_info["basket_address"])

    def test_mint(self) -> None:
        """Test minting a new token vault."""
        basket_address, _ = self.dependency_info["basket"]

        raw_tx = self.contract.mint(
            ledger_api=self.ledger_api,
            contract_address=str(self.contract_address),
            sender_address=self.deployer_crypto.address,
            name="test_name",
            symbol="TST",
            token_address=basket_address,
            token_id=0,
            token_supply=3,
            list_price=1,
            fee=1,
            gas=DEFAULT_GAS,
        )

        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        vault_address = self.contract.get_vault(
            ledger_api=self.ledger_api,
            contract_address=str(self.contract_address),
            index=0,
        )

        assert (
            vault_address != "0x0000000000000000000000000000000000000000"
        ), "couldn't create vault"
