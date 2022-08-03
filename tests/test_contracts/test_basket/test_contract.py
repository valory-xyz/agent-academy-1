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

"""Tests for valory/basket contract."""
import time
from pathlib import Path
from typing import Any, Dict, Optional, cast

from autonomy.test_tools.base_test_classes.contracts import (
    BaseGanacheContractWithDependencyTest,
)

from packages.elcollectooorr.contracts.basket.contract import BasketContract
from packages.elcollectooorr.contracts.basket_factory.contract import (
    BasketFactoryContract,
)

from tests.conftest import ROOT_DIR


DEFAULT_GAS = 10000000
DEFAULT_MAX_FEE_PER_GAS = 10 ** 10
DEFAULT_MAX_PRIORITY_FEE_PER_GAS = 10 ** 10


class TestBasket(BaseGanacheContractWithDependencyTest):
    """Test deployment of the proxy to Ganache."""

    contract_directory = Path(ROOT_DIR, "packages", "valory", "contracts", "basket")
    contract: BasketContract
    dependencies = [
        (
            "basket_factory",
            Path(ROOT_DIR, "packages", "valory", "contracts", "basket_factory"),
            dict(
                gas=DEFAULT_GAS,
            ),
        )
    ]
    create_basket_tx_hash: Optional[str] = None

    @classmethod
    def deploy(cls, **kwargs: Any) -> None:
        """Deploy the contract."""

        is_basket = kwargs.pop("is_basket", False)

        if not is_basket:
            super().deploy(**kwargs)
            return

        tx = cls.contract.get_deploy_transaction(
            ledger_api=cls.ledger_api,
            deployer_address=str(cls.deployer_crypto.address),
            **kwargs,
        )
        if tx is None:
            return None
        tx_signed = cls.deployer_crypto.sign_transaction(tx)
        tx_hash = cls.ledger_api.send_signed_transaction(tx_signed)

        time.sleep(3)  # wait for the transaction to settle

        cls.contract_address = (
            "0x"  # to avoid failing test because of missing contract address
        )
        cls.create_basket_tx_hash = tx_hash

    @classmethod
    def deployment_kwargs(cls) -> Dict[str, Any]:
        """Get deployment kwargs."""
        basket_factory_address, _ = cls.dependency_info["basket_factory"]

        return dict(
            gas=DEFAULT_GAS,
            basket_factory_address=basket_factory_address,
            is_basket=True,
        )

    def test_deploy_and_verify(self) -> None:
        """Test that the contract is deployed, then check if the bytecode is deployed correctly"""

        assert self.create_basket_tx_hash is not None, "createBasket hasn't been called"

        basket_factory_address, basket_factory_contract = self.dependency_info[
            "basket_factory"
        ]
        basket_factory_contract = cast(BasketFactoryContract, basket_factory_contract)

        basket_info = basket_factory_contract.get_basket_address(
            ledger_api=self.ledger_api,
            contract_address=basket_factory_address,
            tx_hash=self.create_basket_tx_hash,
        )

        assert basket_info is not None, "couldn't get the basket data"
        assert (
            basket_info["basket_address"] is not None
        ), "contract_address should not be None"
        assert (
            basket_info["creator_address"] is not None
        ), "creator_address should not be None"
        assert (
            basket_info["creator_address"] == self.deployer_crypto.address
        ), "creator_address doesnt match signer"

        # verify the contract is deployed correctly
        result = self.contract.verify_contract(
            ledger_api=self.ledger_api,
            contract_address=str(basket_info["basket_address"]),
        )

        assert result["verified"], "Contract not verified."
