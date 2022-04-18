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

"""Tests for valory/basket_factory contract."""
import time
from pathlib import Path
from typing import Any, Dict

from aea.crypto.registries import crypto_registry
from aea_ledger_ethereum import EthereumCrypto

from packages.valory.contracts.basket_factory.contract import BasketFactoryContract

from tests.conftest import ETHEREUM_KEY_PATH_1, ROOT_DIR
from tests.test_packages.test_contracts.base import BaseGanacheContractTest


DEFAULT_GAS = 10000000
DEFAULT_MAX_FEE_PER_GAS = 10 ** 10
DEFAULT_MAX_PRIORITY_FEE_PER_GAS = 10 ** 10


class TestBasketFactory(BaseGanacheContractTest):
    """Test deployment of the proxy to Ganache."""

    contract_directory = Path(
        ROOT_DIR, "packages", "valory", "contracts", "basket_factory"
    )
    contract: BasketFactoryContract

    @classmethod
    def deployment_kwargs(cls) -> Dict[str, Any]:
        """Get deployment kwargs."""
        return dict(
            gas=DEFAULT_GAS,
        )

    def test_create_basket(self) -> None:
        """Test creating a basket"""
        sender = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_1
        )

        tx = self.contract.create_basket(
            ledger_api=self.ledger_api,
            factory_contract_address=str(self.contract_address),
            deployer_address=sender.address,
            gas=DEFAULT_GAS,
        )

        assert all(
            [
                key in tx.keys()
                for key in [
                    "value",
                    "chainId",
                    "maxFeePerGas",
                    "maxPriorityFeePerGas",
                    "gas",
                    "nonce",
                    "to",
                    "data",
                ]
            ]
        ), "Missing key"

        tx_signed = sender.sign_transaction(tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash not none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        basket_info = self.contract.get_basket_address(
            self.ledger_api, str(self.contract_address), tx_hash
        )

        assert basket_info is not None, "couldn't get the basket data"
        assert (
            basket_info["basket_address"] is not None
        ), "contract_address should not be None"
        assert (
            basket_info["creator_address"] is not None
        ), "creator_address should not be None"
        assert (
            basket_info["creator_address"] == sender.address
        ), "creator_address doesnt match signer"

    def test_verify(self) -> None:
        """Test verification of deployed contract results."""
        assert self.contract_address is not None
        result = self.contract.verify_contract(
            ledger_api=self.ledger_api,
            contract_address=self.contract_address,
        )

        assert result["verified"], "Contract not verified."
