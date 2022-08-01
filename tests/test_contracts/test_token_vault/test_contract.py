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

"""Tests for valory/token_vault contract."""
import time
from pathlib import Path
from typing import Any, Dict, cast

from aea.crypto.registries import crypto_registry
from aea_ledger_ethereum import EthereumCrypto
from autonomy.test_tools.base_test_classes.contracts import (
    BaseGanacheContractWithDependencyTest,
)

from packages.valory.contracts.basket.contract import BasketContract
from packages.valory.contracts.basket_factory.contract import BasketFactoryContract
from packages.valory.contracts.token_vault.contract import TokenVaultContract
from packages.valory.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)

from tests.conftest import ETHEREUM_KEY_PATH_1, ROOT_DIR


DEFAULT_GAS = 1000000000
DEFAULT_MAX_FEE_PER_GAS = 10 ** 10
DEFAULT_MAX_PRIORITY_FEE_PER_GAS = 10 ** 10


class TestTokenVault(BaseGanacheContractWithDependencyTest):
    """Test deployment of Token Vault to Ganache."""

    contract_directory = Path(
        ROOT_DIR, "packages", "valory", "contracts", "token_vault"
    )
    contract: TokenVaultContract

    dependencies = [
        (
            "token_settings",
            Path(ROOT_DIR, "packages", "valory", "contracts", "token_settings"),
            dict(
                gas=DEFAULT_GAS,
            ),
        ),
        (
            "basket_factory",
            Path(ROOT_DIR, "packages", "valory", "contracts", "basket_factory"),
            dict(
                gas=DEFAULT_GAS,
            ),
        ),
        (
            "basket",
            Path(ROOT_DIR, "packages", "valory", "contracts", "basket"),
            dict(
                gas=DEFAULT_GAS,
                is_basket=True,
            ),
        ),
        (
            "token_vault_factory",
            Path(ROOT_DIR, "packages", "valory", "contracts", "token_vault_factory"),
            dict(gas=DEFAULT_GAS, deps={"_settings": "token_settings"}),
        ),
    ]

    @classmethod
    def deployment_kwargs(cls) -> Dict[str, Any]:
        """Get deployment kwargs."""
        assert (
            cls.dependency_info["token_settings"] is not None
        ), "token_settings is not ready"

        basket_address, _ = cls.dependency_info["basket"]
        vault_factory_address, _ = cls.dependency_info["token_vault_factory"]

        return dict(
            is_token_vault=True,
            gas=DEFAULT_GAS,
            token_vault_factory_address=vault_factory_address,
            name="test_name",
            symbol="TST",
            token_address=basket_address,
            token_id=0,
            token_supply=3,
            list_price=1,
            fee=1,
        )

    @classmethod
    def _deploy_basket(cls, **kwargs: Any) -> None:
        """Deploy basket"""

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

    @classmethod
    def _permission_vault_factory(cls) -> None:
        """Permission the vault factory to use the basket"""

        basket_address, basket_contract = cls.dependency_info["basket"]
        basket_contract = cast(BasketContract, basket_contract)
        vault_factory_address, _ = cls.dependency_info["token_vault_factory"]
        raw_tx = basket_contract.set_approve_for_all(
            ledger_api=cls.ledger_api,
            contract_address=basket_address,
            sender_address=cls.deployer_crypto.address,
            operator_address=vault_factory_address,
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
    def _deploy_token_vault(cls, **kwargs: Any) -> None:
        """Deploy the Token Vault"""
        tx = cls.contract.get_deploy_transaction(
            ledger_api=cls.ledger_api,
            deployer_address=str(cls.deployer_crypto.address),
            **kwargs,
        )
        if tx is None:
            return None
        tx_signed = cls.deployer_crypto.sign_transaction(tx)
        cls.ledger_api.send_signed_transaction(tx_signed)

        time.sleep(3)  # wait for the transaction to settle

        address, contract = cls.dependency_info["token_vault_factory"]
        contract = cast(TokenVaultFactoryContract, contract)

        cls.contract_address = contract.get_vault(
            ledger_api=cls.ledger_api,
            contract_address=address,
            index=0,
        )

        assert (
            cls.contract_address != "0x0000000000000000000000000000000000000000"
        ), "couldn't create vault"

    @classmethod
    def deploy(cls, **kwargs: Any) -> None:
        """Deploy the contract."""

        is_basket = kwargs.pop("is_basket", False)
        is_token_vault = kwargs.pop("is_token_vault", False)

        if is_basket:
            cls._deploy_basket(**kwargs)
            return

        if is_token_vault:
            cls._permission_vault_factory()
            cls._deploy_token_vault(**kwargs)
            return

        super().deploy(**kwargs)

    def test_verify(self) -> None:
        """Test verification of deployed contract results."""
        assert self.contract_address is not None
        settings_address, _ = self.dependency_info["token_settings"]

        result = self.contract.verify_contract(
            ledger_api=self.ledger_api,
            contract_address=self.contract_address,
        )

        assert result["verified"], "The bytecode was incorrect."

    def test_kick_curator(self) -> None:
        """The owner changes the curator"""

        new_curator = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_1
        )

        raw_tx = self.contract.kick_curator(
            ledger_api=self.ledger_api,
            contract_address=str(self.contract_address),
            sender_address=self.deployer_crypto.address,
            curator_address=new_curator.address,
            gas=DEFAULT_GAS,
        )

        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        contract = TokenVaultContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = contract.functions.curator().call()
        expected_value = new_curator.address

        assert actual_value == expected_value, "curator was not updated"

    def test_transfer(self) -> None:
        """The owner can remove the reserve price of a user"""

        receiver = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_1
        )

        raw_tx = self.contract.transfer_erc20(
            ledger_api=self.ledger_api,
            contract_address=str(self.contract_address),
            sender_address=self.deployer_crypto.address,
            receiver_address=receiver.address,
            amount=3,
            gas=DEFAULT_GAS,
        )

        tx_signed = self.deployer_crypto.sign_transaction(raw_tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        contract = TokenVaultContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = contract.functions.balanceOf(receiver.address).call()
        expected_value = 3

        assert actual_value == expected_value, "transfer of tokens was not made"

    def test_get_balance(self) -> None:
        """Test that get_balance returns the correct value"""

        contract = TokenVaultContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_balance(
            self.ledger_api,
            str(self.contract_address),
            self.deployer_crypto.address,
        )["balance"]

        expected_value = contract.functions.balanceOf(
            self.deployer_crypto.address
        ).call()

        assert actual_value == expected_value, "get_balance returned the wrong value"

    def test_get_curator(self) -> None:
        """Test that get_curator returns the correct value"""

        contract = TokenVaultContract.get_instance(
            self.ledger_api, self.contract_address
        )

        actual_value = self.contract.get_curator(
            self.ledger_api,
            str(self.contract_address),
        )

        expected_value = contract.functions.curator().call()

        assert actual_value == expected_value, "get_curator returned the wrong value"
