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
import json
from abc import ABC
from typing import Generator, List, Set, Type, cast

from aea.exceptions import AEAEnforceError, enforce

from packages.valory.contracts.basket.contract import BasketContract
from packages.valory.contracts.basket_factory.contract import BasketFactoryContract
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.contracts.token_vault.contract import TokenVaultContract
from packages.valory.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.fractionalize_deployment_abci.models import Params
from packages.valory.skills.fractionalize_deployment_abci.payloads import (
    BasketAddressesPayload,
    DeployBasketPayload,
    DeployDecisionPayload,
    DeployVaultPayload,
    PermissionVaultFactoryPayload,
    VaultAddressesPayload,
)
from packages.valory.skills.fractionalize_deployment_abci.rounds import (
    BasketAddressRound,
    DeployBasketAbciApp,
    DeployBasketTxRound,
    DeployDecisionRound,
    DeployVaultAbciApp,
    DeployVaultTxRound,
    FinishedDeployBasketTxRound,
    FinishedDeployVaultTxRound,
    PeriodState,
    PermissionVaultFactoryRound,
    PostBasketDeploymentAbciApp,
    PostVaultDeploymentAbciApp,
    VaultAddressRound,
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


class FractionalizeDeploymentABCIBaseState(BaseState, ABC):
    """Base state behaviour for the Fractionalize Deployment abci skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, self.context.state.period_state)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class DeployDecisionRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Behaviour for deciding whether a new basket & vault should be deployed"""

    state_id = "deploy_decision_round_behaviour"
    matching_round = DeployDecisionRound

    def async_act(self) -> Generator:
        """Implement the act."""
        with self.context.benchmark_tool.measure(
            self,
        ).local():
            should_deploy = False

            try:
                vault_addresses = cast(
                    List[str], self.period_state.db.get("vault_addresses", [])
                )
                amount_spent = self.period_state.db.get("amount_spent", 0)
                budget = self.params.budget_per_vault - (
                    0.15 * (10 ** 18)
                )  # we leave a 0.15ETH margin

                if len(vault_addresses) == 0:
                    # no vaults are deployed, so a new one needs to get deployed
                    should_deploy = True

                elif amount_spent >= budget:
                    should_deploy = True

                else:
                    latest_vault = vault_addresses[-1]
                    status = yield from self._get_vault_state(latest_vault)

                    if status != 0:
                        # the state is not Inactive, the reserve has been met
                        should_deploy = True

                    if not should_deploy:
                        tokens_left = yield from self._get_num_tokens_left(latest_vault)
                        should_deploy = (
                            tokens_left == 0
                        )  # if no tokens are left, the vault has sold out, deploy a new one

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create the DeployDecisionRound payload, {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            self.context.logger.info(f"Deploy new basket and vault? {should_deploy}.")

            payload = DeployDecisionPayload(
                self.context.agent_address,
                should_deploy,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_vault_state(self, vault_address: str) -> Generator[None, None, int]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_id=str(TokenVaultContract.contract_id),
            contract_callable="get_auction_state",
            contract_address=vault_address,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "state" in response.state.body.keys()
            and response.state.body["state"] is not None,
            "response, response.state, response.state.body must exist",
        )

        data = cast(int, response.state.body["state"])

        return data

    def _get_num_tokens_left(self, vault_address: str) -> Generator[None, None, int]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_id=str(TokenVaultContract.contract_id),
            contract_callable="get_balance",
            contract_address=vault_address,
            address=self.period_state.db.get_strict("safe_contract_address"),
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "balance" in response.state.body.keys()
            and response.state.body["balance"] is not None,
            "response, response.state, response.state.body must exist",
        )

        data = cast(int, response.state.body["balance"])

        return data


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
                self.context.logger.error(
                    f"Couldn't create DeployBasketTxRound payload, {type(e).__name__}: {e}."
                )

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
                    to_address=self.params.token_vault_factory_address,
                    data=mint_data,
                )

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create DeployVaultTxRound payload, {type(e).__name__}: {e}."
                )

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
            to_address=self.params.token_vault_factory_address,
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
        all_baskets = cast(
            List[str], self.period_state.db.get_strict("basket_addresses")
        )
        latest_basket = all_baskets[-1]

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.token_vault_factory_address,
            contract_id=str(TokenVaultFactoryContract.contract_id),
            contract_callable="mint_abi",
            name=f"El Collectooorr Vault #{len(all_baskets)}",
            symbol="ELC",
            token_address=latest_basket,
            token_id=0,
            token_supply=1000,
            list_price=0,
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


class BasketAddressesRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Behaviour of basket addresses round"""

    state_id = "basket_address_round_behaviour"
    matching_round = BasketAddressRound

    def async_act(self) -> Generator:
        """Implement the act."""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            try:
                basket_addresses = cast(
                    List[str], self.period_state.db.get("basket_addresses", [])
                )
                new_basket = yield from self._get_basket()
                basket_addresses.append(new_basket)
                self.context.logger.info(f"New basket address={new_basket}")
            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create BasketAddressRound payload, {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = BasketAddressesPayload(
                self.context.agent_address,
                json.dumps(basket_addresses),
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_basket(self) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.basket_factory_address,
            contract_id=str(BasketFactoryContract.contract_id),
            contract_callable="get_basket_address",
            tx_hash=self.period_state.db.get("final_tx_hash"),
        )

        # response body also has project details
        enforce(
            response.state.body is not None
            and "basket_address" in response.state.body.keys(),
            "couldn't extract the 'basket_address' from the BaketFactoryContract",
        )

        data = cast(str, response.state.body["basket_address"])

        return data


class PermissionVaultFactoryRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Defines the DeployBasketTxRoundRound behaviour"""

    state_id = "permission_vault_factory"
    matching_round = PermissionVaultFactoryRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            try:
                latest_basket = cast(
                    List[str], self.period_state.db.get_strict("basket_addresses")
                )[-1]
                basket_data_str = yield from self._get_permission_tx()
                basket_data = bytes.fromhex(basket_data_str[2:])
                tx_hash = yield from self._get_safe_hash(basket_data)

                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=0,
                    safe_tx_gas=10 ** 7,
                    to_address=latest_basket,
                    data=basket_data,
                )

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create PermissionVaultFactoryRound payload, {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = PermissionVaultFactoryPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, data: bytes) -> Generator[None, None, str]:
        latest_basket = cast(
            List[str], self.period_state.db.get_strict("basket_addresses")
        )[-1]

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.db.get("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=latest_basket,
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

    def _get_permission_tx(self) -> Generator[None, None, str]:
        latest_basket = cast(List[str], self.period_state.db.get("basket_addresses"))[
            -1
        ]

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_id=str(BasketContract.contract_id),
            contract_callable="approve_abi",
            contract_address=latest_basket,
            operator_address=self.params.token_vault_factory_address,
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


class VaultAddressesRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Behaviour of vault addresses round"""

    state_id = "vault_address_round_behaviour"
    matching_round = VaultAddressRound

    def async_act(self) -> Generator:
        """Implement the act."""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            try:
                vault_addresses = cast(
                    List[str], self.period_state.db.get("vault_addresses", [])
                )
                new_vault = yield from self._get_vault()
                vault_addresses.append(new_vault)

                self.context.logger.info(f"Deployed new TokenVault at: {new_vault}.")
            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create VaultAddressesRoundBehaviour payload, {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = VaultAddressesPayload(
                self.context.agent_address,
                json.dumps(vault_addresses),
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_vault(self) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.token_vault_factory_address,
            contract_id=str(TokenVaultFactoryContract.contract_id),
            contract_callable="get_vault_address",
            tx_hash=self.period_state.db.get("final_tx_hash"),
        )

        # response body also has project details
        enforce(
            response.state.body is not None
            and "vault_address" in response.state.body.keys(),
            "couldn't extract vault_address from the vault_factory",
        )

        data = cast(str, response.state.body["vault_address"])

        return data


class FinishedTokenVaultTxRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Degenerate behaviour for a degenerate round"""

    matching_round = FinishedDeployVaultTxRound
    state_id = "finished_deploy_vault_tx"

    def async_act(self) -> Generator:
        """Simply log that the app was executed successfully."""
        self.context.logger.info(
            "Successfully executed Fractionalize Deployment TX app."
        )
        self.set_done()
        yield


class FinishedDeployBasketTxRoundBehaviour(FractionalizeDeploymentABCIBaseState):
    """Degenerate behaviour for a degenerate round"""

    matching_round = FinishedDeployBasketTxRound
    state_id = "finished_deploy_basket_tx_behaviour"

    def async_act(self) -> Generator:
        """Simply log that the app was executed successfully."""
        self.context.logger.info("Successfully executed Basket Deployment TX.")
        self.set_done()
        yield


class DeployVaultRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Vault Deployment abci app."""

    initial_state_cls = DeployTokenVaultTxRoundBehaviour
    abci_app_cls = DeployVaultAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        DeployTokenVaultTxRoundBehaviour,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger


class DeployBasketRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Basket Deployment abci app."""

    initial_state_cls = DeployDecisionRoundBehaviour
    abci_app_cls = DeployBasketAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        DeployDecisionRoundBehaviour,
        DeployBasketTxRoundBehaviour,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger


class PostBasketDeploymentRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Basket Deployment abci app."""

    initial_state_cls = BasketAddressesRoundBehaviour
    abci_app_cls = PostBasketDeploymentAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        BasketAddressesRoundBehaviour,
        PermissionVaultFactoryRoundBehaviour,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger


class PostVaultDeploymentRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Vault Deployment abci app."""

    initial_state_cls = VaultAddressesRoundBehaviour
    abci_app_cls = PostVaultDeploymentAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        VaultAddressesRoundBehaviour,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger
