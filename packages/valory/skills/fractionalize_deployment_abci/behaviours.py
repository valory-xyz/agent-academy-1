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

"""This module contains the behaviour_classes for the 'fractionalize_deployment_abci' skill."""

from abc import ABC
from typing import Generator, Set, Type, cast

from aea.exceptions import AEAEnforceError, enforce

from packages.valory.contracts.basket_factory.contract import BasketFactoryContract
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.contracts.token_vault_factory.contract import TokenVaultFactoryContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.fractionalize_deployment_abci.models import SharedState, Params
from packages.valory.skills.fractionalize_deployment_abci.payloads import DeployBasketPayload, DeployVaultPayload
from packages.valory.skills.fractionalize_deployment_abci.rounds import PeriodState, DeployBasketTxRound, \
    FinishedDeployVaultTxRound, FractionalizeDeploymentAbciApp, DeployVaultTxRound, \
    BasketTransactionRounds, VaultTransactionRounds, VaultTransactionSubmissionAbciApp, \
    BasketTransactionSubmissionAbciApp
from packages.valory.skills.registration_abci.behaviours import (
    AgentRegistrationRoundBehaviour,
)
from packages.valory.skills.safe_deployment_abci.behaviours import SafeDeploymentRoundBehaviour
from packages.valory.skills.transaction_settlement_abci.behaviours import TransactionBehaviours, \
    TransactionSettlementRoundBehaviour
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


class FractionalizeDeploymentABCIBaseState(BaseState, ABC):
    """Base state behaviour for the Fractionalize Deployment abci skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, cast(SharedState, self.context.state).period_state)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class DeployBasketTxRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Defines the DeployBasketTxRoundRound behaviour"""

    state_id = "deploy_basket_transaction_collection"
    matching_round = DeployBasketTxRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
                self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            try:
                basket_data_str = yield from self._get_create_basket()
                basket_data = bytes.fromhex(basket_data_str[2:])
                tx_hash = yield from self._get_safe_hash(basket_data)

                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=0,
                    safe_tx_gas=10 ** 7,
                    to_address=self.params.basket_factory_address,
                    data=basket_data,
                )

            except AEAEnforceError as e:
                self.context.logger.error(f"couldn't create transaction payload, e={e}")

        with self.context.benchmark_tool.measure(
                self,
        ).consensus():
            payload = DeployBasketPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, data: bytes) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.db.get("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.params.basket_factory_address,
            value=0,
            data=data,
            safe_tx_gas=10 ** 7,
        )

        enforce(
            response.state.body is not None
            and "tx_hash" in response.state.body.keys()
            and response.state.body["tx_hash"] is not None,
            "contract returned and empty body or empty tx_hash",
        )

        tx_hash = cast(str, response.state.body["tx_hash"])[2:]

        return tx_hash

    def _get_create_basket(self) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_id=str(BasketFactoryContract.contract_id),
            contract_callable="create_basket_abi",
            contract_address=self.params.basket_factory_address,
        )

        # response body also has project details
        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        data = cast(str, response.state.body["data"])

        return data

    def _format_payload(self, tx_hash: str, data: str) -> str:
        tx_hash = tx_hash[2:]
        ether_value = int.to_bytes(0, 32, "big").hex().__str__()
        safe_tx_gas = int.to_bytes(10 ** 7, 32, "big").hex().__str__()
        address = self.params.basket_factory_address
        data = data[2:]  # remove starting '0x'

        return f"{tx_hash}{ether_value}{safe_tx_gas}{address}{data}"


class DeployTokenVaultTxRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Defines the DeployBasketTxRoundRound behaviour"""

    state_id = "deploy_vault_transaction_collection"
    matching_round = DeployVaultTxRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
                self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            try:
                mint_data_str = yield from self._get_mint_vault()
                mint_data = bytes.fromhex(mint_data_str[2:])
                tx_hash = yield from self._get_safe_hash(mint_data)

                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=0,
                    safe_tx_gas=10 ** 7,
                    to_address=self.params.basket_factory_address,
                    data=mint_data,
                )

            except AEAEnforceError as e:
                self.context.logger.error(f"couldn't create transaction payload, e={e}")

        with self.context.benchmark_tool.measure(
                self,
        ).consensus():
            payload = DeployVaultPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, data: bytes) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.db.get("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.params.basket_factory_address,
            value=0,
            data=data,
            safe_tx_gas=10 ** 7,
        )

        enforce(
            response.state.body is not None
            and "tx_hash" in response.state.body.keys()
            and response.state.body["tx_hash"] is not None,
            "contract returned and empty body or empty tx_hash",
        )

        tx_hash = cast(str, response.state.body["tx_hash"])[2:]

        return tx_hash

    def _get_mint_vault(self) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.basket_factory_address,
            contract_id=str(TokenVaultFactoryContract.contract_id),
            contract_callable="mint_abi",
            name="test_vault",
            symbol="TSV",
            token_address="0x3B3ee1931Dc30C1957379FAc9aba94D1C48a5405",
            token_id=1,
            token_supply=100,
            list_price=1,
            fee=1,
        )

        # response body also has project details
        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        data = cast(str, response.state.body["data"])

        return data

    def _format_payload(self, tx_hash: str, data: str) -> str:
        tx_hash = tx_hash[2:]
        ether_value = int.to_bytes(0, 32, "big").hex().__str__()
        safe_tx_gas = int.to_bytes(10 ** 7, 32, "big").hex().__str__()
        address = self.params.basket_factory_address
        data = data[2:]  # remove starting '0x'

        return f"{tx_hash}{ether_value}{safe_tx_gas}{address}{data}"


class FinishedTokenVaultTxRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Degenerate behaviour for a degenerate round"""

    matching_round = FinishedDeployVaultTxRound
    state_id = "finished_deploy_vault_tx"

    def async_act(self) -> Generator:
        """Simply log that the app was executed successfully."""
        self.context.logger.info("Successfully executed Fractionalize Deployment TX app.")
        self.set_done()
        yield


class VaultTransactionBehaviours(TransactionBehaviours):
    """Wrapper around transaction rounds"""
    transaction_rounds = VaultTransactionRounds


class BasketTransactionBehaviours(TransactionBehaviours):
    """Wrapper around transaction rounds"""
    transaction_rounds = BasketTransactionRounds


class VaultTransactionSubmissionRoundBehaviour(TransactionSettlementRoundBehaviour):
    """Wrapper around transaction rounds"""
    behaviours = VaultTransactionBehaviours
    abci_app_cls = VaultTransactionSubmissionAbciApp


class BasketTransactionSubmissionRoundBehaviour(TransactionSettlementRoundBehaviour):
    """Wrapper around transaction rounds"""
    behaviours = BasketTransactionBehaviours
    abci_app_cls = BasketTransactionSubmissionAbciApp


class FractionalizeDeploymentFullRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Fractionalize Deployment abci app."""

    initial_state_cls = AgentRegistrationRoundBehaviour.initial_state_cls
    abci_app_cls = FractionalizeDeploymentAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        *AgentRegistrationRoundBehaviour.behaviour_states,
        *VaultTransactionSubmissionRoundBehaviour.behaviour_states,
        *BasketTransactionSubmissionRoundBehaviour.behaviour_states,
        *SafeDeploymentRoundBehaviour.behaviour_states,
        DeployBasketTxRoundBehaviour,
        DeployTokenVaultTxRoundBehaviour,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger
