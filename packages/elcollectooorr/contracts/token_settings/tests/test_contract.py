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
# pylint: skip-file

"""Tests for valory/token_settings contract."""
import time
from pathlib import Path
from typing import Any, Dict

from aea.crypto.registries import crypto_registry
from aea_ledger_ethereum import EthereumCrypto
from aea_test_autonomy.base_test_classes.contracts import BaseGanacheContractTest
from aea_test_autonomy.configurations import ETHEREUM_KEY_PATH_2
from aea_test_autonomy.docker.base import skip_docker_tests

from packages.elcollectooorr.contracts.token_settings.contract import (
    TokenSettingsContract,
)


DEFAULT_GAS = 10000000
DEFAULT_MAX_FEE_PER_GAS = 10 ** 10
DEFAULT_MAX_PRIORITY_FEE_PER_GAS = 10 ** 10


@skip_docker_tests
class TestTokenSettingsFactory(BaseGanacheContractTest):
    """Test deployment of Token Settings to Ganache."""

    CONTRACTS_DIR = Path(__file__).parent.parent.parent
    contract_directory = Path(CONTRACTS_DIR, "token_settings")
    contract: TokenSettingsContract

    @classmethod
    def deployment_kwargs(cls) -> Dict[str, Any]:
        """Get deployment kwargs."""
        return dict(
            gas=DEFAULT_GAS,
        )

    def test_transfer_ownership(self) -> None:
        """Test fee_reciever change then test ownership change"""

        # test changing fee receiver
        new_receiver = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_2
        )

        tx = self.contract.set_fee_receiver(
            ledger_api=self.ledger_api,
            contract_address=str(self.contract_address),
            owner_address=self.deployer_crypto.address,
            new_receiver_address=new_receiver.address,
            gas=DEFAULT_GAS,
        )

        tx_signed = self.deployer_crypto.sign_transaction(tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        contract = TokenSettingsContract.get_instance(
            self.ledger_api, contract_address=self.contract_address
        )
        fee_receiver = contract.functions.feeReceiver().call()

        assert (
            fee_receiver == new_receiver.address
        ), f"Expected the fee receiver to be: {new_receiver.address}"

        # test changing owner
        new_owner = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_2
        )

        tx = self.contract.transfer_ownership(
            ledger_api=self.ledger_api,
            contract_address=str(self.contract_address),
            current_owner_address=self.deployer_crypto.address,
            new_owner_address=new_owner.address,
            gas=DEFAULT_GAS,
        )

        tx_signed = self.deployer_crypto.sign_transaction(tx)
        tx_hash = self.ledger_api.send_signed_transaction(tx_signed)

        assert tx_hash is not None, "Tx hash is none"

        time.sleep(3)  # give 3 seconds for the transaction to go through

        contract = TokenSettingsContract.get_instance(
            self.ledger_api, contract_address=self.contract_address
        )
        contract_owner = contract.functions.owner().call()

        assert (
            contract_owner == new_owner.address
        ), f"Expected the owner to be: {new_owner.address}"

    def test_verify(self) -> None:
        """Test verification of deployed contract results."""
        new_receiver = crypto_registry.make(
            EthereumCrypto.identifier, private_key_path=ETHEREUM_KEY_PATH_2
        )

        assert self.contract_address is not None
        result = self.contract.verify_contract(
            ledger_api=self.ledger_api,
            contract_address=self.contract_address,
            expected_owner_address=new_receiver.address,
        )

        assert result["bytecode"], "The bytecode was incorrect."
