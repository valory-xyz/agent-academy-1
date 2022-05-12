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

"""This module contains the behaviour_classes for the 'elcollectooorr_abci' skill."""

import json
from abc import ABC
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Type, Union, cast

from aea.common import JSONLike
from aea.exceptions import AEAEnforceError, enforce
from hexbytes import HexBytes

from packages.valory.contracts.artblocks.contract import ArtBlocksContract
from packages.valory.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.valory.contracts.gnosis_safe.contract import (
    GnosisSafeContract,
    SafeOperation,
)
from packages.valory.contracts.multisend.contract import (
    MultiSendContract,
    MultiSendOperation,
)
from packages.valory.contracts.token_vault.contract import TokenVaultContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.elcollectooorr_abci.decision_models import (
    EightyPercentDecisionModel,
)
from packages.valory.skills.elcollectooorr_abci.models import Params, SharedState
from packages.valory.skills.elcollectooorr_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    FundingPayload,
    ObservationPayload,
    PayoutFractionsPayload,
    PostTxPayload,
    PurchasedNFTPayload,
    ResetPayload,
    TransactionPayload,
    TransferNFTPayload,
)
from packages.valory.skills.elcollectooorr_abci.rounds import (
    BankAbciApp,
    DecisionRound,
    DetailsRound,
    ElCollectooorrAbciApp,
    ElcollectooorrBaseAbciApp,
    FundingRound,
    ObservationRound,
    PayoutFractionsRound,
    PeriodState,
    PostFractionPayoutAbciApp,
    PostPayoutRound,
    PostTransactionSettlementRound,
    ProcessPurchaseRound,
    TransactionRound,
    TransactionSettlementAbciMultiplexer,
    TransferNFTAbciApp,
    TransferNFTRound,
)
from packages.valory.skills.fractionalize_deployment_abci.behaviours import (
    DeployBasketRoundBehaviour,
    DeployVaultRoundBehaviour,
    PostBasketDeploymentRoundBehaviour,
    PostVaultDeploymentRoundBehaviour,
)
from packages.valory.skills.registration_abci.behaviours import (
    AgentRegistrationRoundBehaviour,
    RegistrationStartupBehaviour,
)
from packages.valory.skills.safe_deployment_abci.behaviours import (
    SafeDeploymentRoundBehaviour,
)
from packages.valory.skills.transaction_settlement_abci.behaviours import (
    TransactionSettlementRoundBehaviour,
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


class ElcollectooorrABCIBaseState(BaseState, ABC):
    """Base state behaviour for the El Collectooorr abci skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, cast(SharedState, self.context.state).period_state)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class BaseResetBehaviour(ElcollectooorrABCIBaseState):
    """Reset state."""

    pause = True

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Trivially log the state.
        - Sleep for configured interval.
        - Build a registration transaction.
        - Send the transaction and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour state (set done event).
        """
        if self.pause:
            self.context.logger.info("Period end.")
            self.context.benchmark_tool.save()
            yield from self.sleep(self.params.observation_interval)
        else:
            self.context.logger.info(
                f"Period {self.period_state.period_count} was not finished. Resetting!"
            )

        payload = ResetPayload(
            self.context.agent_address, self.period_state.period_count + 1
        )

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class ObservationRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Observation round behaviour"""

    state_id = "observation"
    matching_round = ObservationRound

    def async_act(self) -> Generator:
        """The observation act."""
        with self.context.benchmark_tool.measure(
            self,
        ).local():
            payload_data = {}

            try:
                prev_finished = cast(
                    List[int], self.period_state.db.get("finished_projects", [])
                )
                prev_active = cast(
                    List[Dict], self.period_state.db.get("active_projects", [])
                )
                prev_inactive = cast(
                    List[int], self.period_state.db.get("inactive_projects", [])
                )
                most_recent_project = cast(
                    int, self.period_state.db.get("most_recent_project", 0)
                )

                if most_recent_project == 0:
                    projects_to_check = None
                else:
                    projects_to_check = prev_inactive + [
                        p["project_id"] for p in prev_active
                    ]

                (
                    current_finished_projects,
                    active_projects,
                    inactive_projects,
                ) = yield from self._get_projects(
                    last_processed_project=most_recent_project,
                    project_ids=projects_to_check,
                )

                newly_finished_projects = self._list_diff(
                    current_finished_projects, prev_finished
                )
                most_recent_project = max(
                    current_finished_projects
                    + [p["project_id"] for p in active_projects]
                    + inactive_projects
                )

                payload_data = {
                    "active_projects": active_projects,
                    "inactive_projects": inactive_projects,
                    "newly_finished_projects": newly_finished_projects,
                    "most_recent_project": most_recent_project,
                }

                self.context.logger.info(
                    f"Most recent project is {most_recent_project}."
                )
                self.context.logger.info(
                    f"There are {len(newly_finished_projects)} newly finished projects."
                )
                self.context.logger.info(
                    f"There are {len(active_projects)} active projects."
                )

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't get the projects, the following error was encountered {type(e).__name__}: {e}"
                )

            with self.context.benchmark_tool.measure(
                self,
            ).consensus():
                payload = ObservationPayload(
                    self.context.agent_address,
                    json.dumps(payload_data),
                )

                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

        self.set_done()

    @staticmethod
    def _list_diff(l1: List[Any], l2: List[Any]) -> List[Any]:
        return list(set(l1) - set(l2))

    def _get_projects(
        self,
        last_processed_project: Optional[int] = None,
        project_ids: Optional[List[int]] = None,
    ) -> Generator[None, None, Tuple[List[int], List[Dict], List[int]]]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="get_multiple_projects_info",
            project_ids=project_ids,
            last_processed_project=last_processed_project,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "results" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        all_projects = cast(List[Dict[str, Any]], response.state.body["results"])
        finished_projects, inactive_projects, active_projects = [], [], []

        for project in all_projects:
            project_id = int(project["project_id"])
            max_invocations = int(project["max_invocations"])
            invocations = int(project["invocations"])
            price_per_token_in_wei = int(project["price_per_token_in_wei"])
            is_active = project["is_active"]

            if max_invocations == 0 or invocations / max_invocations == 1:
                finished_projects.append(project_id)
            elif is_active:
                active_projects.append(
                    {
                        "project_id": project_id,
                        "minted_percentage": invocations / max_invocations,
                        "price": price_per_token_in_wei,
                        "is_active": is_active,
                    }
                )
            else:
                inactive_projects.append(project_id)

        return finished_projects, active_projects, inactive_projects


class DetailsRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Details Round behaviour"""

    state_id = "details"
    matching_round = DetailsRound

    def async_act(self) -> Generator:
        """The details act"""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            payload_data = {}

            try:
                active_projects = self.period_state.db.get_strict("active_projects")
                enhanced_projects = yield from self._enhance_active_projects(
                    active_projects
                )
                payload_data = {"active_projects": enhanced_projects}

            except (AEAEnforceError, ValueError, RuntimeError) as e:
                self.context.logger.error(
                    f"Couldn't get projects details, the following error was encountered {type(e).__name__}: {e}"
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = DetailsPayload(
                self.context.agent_address,
                json.dumps(payload_data),
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _enhance_active_projects(
        self, projects: List[Dict]
    ) -> Generator[None, None, List]:
        """Enhance the project data with 'mintable' and 'curation status'."""
        enhanced_projects = []
        are_mintable = yield from self._are_mintable(projects)
        curated_projects = yield from self._get_curated_projects()

        for project in projects:
            project_id = project["project_id"]
            project["is_mintable"] = are_mintable[project_id]
            project["is_curated"] = project_id in curated_projects

            enhanced_projects.append(project)

        return enhanced_projects

    def _are_mintable(self, projects: List[Dict]) -> Generator[None, None, Dict]:
        """Check if the projects are mintable via contracts."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_periphery_contract,
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            contract_callable="are_projects_mintable",
            project_ids=[p["project_id"] for p in projects],
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None,
            "response, response.state, response.state.body must exist",
        )

        are_mintable = cast(Dict, response.state.body)

        enforce(
            len(are_mintable) == len(projects),
            "Invalid response was received from 'are_projects_mintable'.",
        )

        return are_mintable

    def _get_curated_projects(self) -> Generator[None, None, List[int]]:
        """Get a list of curated projects."""
        query = '{projects(where:{curationStatus:"curated"}){projectId}}'
        response = yield from self.get_http_response(
            method="POST",
            url=self.params.artblocks_graph_url,
            content=json.dumps({"query": query}).encode(),
        )

        enforce(
            response is not None
            and response.status_code == 200
            and response.body is not None,
            "Bad response from the graph api.",
        )

        response_body = json.loads(response.body)

        enforce(
            "data" in response_body.keys() and "projects" in response_body["data"],
            "Bad response from the graph api.",
        )

        curated_projects = response_body["data"]["projects"]
        curated_project_ids = [int(p["projectId"]) for p in curated_projects]

        return curated_project_ids


class DecisionRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Decision Round behaviour"""

    state_id = "decision"
    matching_round = DecisionRound

    def async_act(self) -> Generator:
        """The Decision act"""
        with self.context.benchmark_tool.measure(
            self,
        ).local():
            project_to_purchase: Optional[Dict] = {}

            try:
                active_projects = cast(
                    List[Dict], self.period_state.db.get_strict("active_projects")
                )
                purchased_projects = cast(
                    List[Dict], self.period_state.db.get("purchased_projects", [])
                )  # NOTE: projects NOT tokens
                already_spent = cast(
                    int, self.period_state.db.get_strict("amount_spent")
                )
                safe_balance = yield from self._get_safe_balance()
                current_budget = min(
                    self.params.budget_per_vault - already_spent, safe_balance
                )

                self.context.logger.info(
                    f"The safe contract balance is {safe_balance / 10 ** 18}Ξ."
                )
                self.context.logger.info(f"Already spent {already_spent / 10 ** 18}Ξ.")
                self.context.logger.info(
                    f"The current budget is {current_budget / 10 ** 18}Ξ."
                )

                project_to_purchase = self._get_project_to_purchase(
                    active_projects=active_projects,
                    purchased_projects=purchased_projects,
                    budget=current_budget,
                )

                if project_to_purchase is None:
                    # right now {} represents no project
                    project_to_purchase = {}

            except (AEAEnforceError, ValueError, RuntimeError) as e:
                self.context.logger.error(
                    f"Couldn't make a decision, the following error was encountered {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            project_to_purchase = cast(Dict, project_to_purchase)
            payload = DecisionPayload(
                sender=self.context.agent_address,
                decision=json.dumps(project_to_purchase),
            )
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_project_to_purchase(
        self,
        active_projects: List[dict],
        purchased_projects: List[dict],
        budget: int,
    ) -> Optional[Dict]:
        """Get the fittest project to purchase."""

        projects = EightyPercentDecisionModel.decide(
            active_projects, purchased_projects, budget
        )
        self.context.logger.info(f"{len(projects)} projects fit the reqs.")

        if len(projects) == 0:
            return None

        return projects[0]  # the first project is the fittest

    def _get_safe_balance(self) -> Generator[None, None, int]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.period_state.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_balance",
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None,
            "response, response.state, response.state.body must exist",
        )

        return cast(int, response.state.body["balance"])


class TransactionRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Transaction Round behaviour"""

    state_id = "transaction_collection"
    matching_round = TransactionRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            try:
                project_to_purchase = self.period_state.db.get_strict(
                    "project_to_purchase"
                )
                value = project_to_purchase[
                    "price"
                ]  # price of token in the project in wei
                purchase_data_str = yield from self._get_purchase_data(
                    project_to_purchase["project_id"]
                )
                purchase_data = bytes.fromhex(purchase_data_str[2:])
                tx_hash = yield from self._get_safe_hash(
                    data=purchase_data, value=value
                )
                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=value,
                    safe_tx_gas=10 ** 7,
                    to_address=self.params.artblocks_periphery_contract,
                    data=purchase_data,
                )

            except (AEAEnforceError, ValueError) as e:
                self.context.logger.error(
                    f"Couldn't create transaction payload, the following error was encountered {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = TransactionPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, data: bytes, value: int = 0) -> Generator[None, None, str]:
        """Get the safe hash."""

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.params.artblocks_periphery_contract,
            value=value,
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

    def _get_purchase_data(self, project_id: int) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_periphery_contract,
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            contract_callable="purchase_data",
            project_id=project_id,
        )

        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        purchase_data = cast(str, response.state.body["data"])

        return purchase_data


class FundingRoundBehaviour(ElcollectooorrABCIBaseState):
    """Checks the balance of the safe contract."""

    state_id = "funding_behaviour"
    matching_round = FundingRound

    def async_act(self) -> Generator:
        """Get the available funds and store them to state."""

        with self.context.benchmark_tool.measure(self.state_id).local():
            in_transfers = yield from self._get_available_funds()
            payload = FundingPayload(
                self.context.agent_address,
                address_to_funds=json.dumps(in_transfers),
            )

        with self.context.benchmark_tool.measure(self.state_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_available_funds(
        self, from_block: Optional[int] = None, to_block: Union[str, int] = "latest"
    ) -> Generator:
        """Returns all the transfers to the gnosis safe."""

        in_transfers = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.period_state.db.get("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_ingoing_transfers",
            from_block=from_block,
            to_block=to_block,
        )

        return in_transfers.state.body["data"]


class PayoutFractionsRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the DeployBasketTxRoundRound behaviour"""

    state_id = "payout_fractions"
    matching_round = PayoutFractionsRound

    def async_act(self) -> Generator:
        """Implement the act."""
        with self.context.benchmark_tool.measure(
            self,
        ).local():
            try:
                latest_vault = cast(
                    List[str], self.period_state.db.get("vault_addresses")
                )[-1]
                multisend_data_obj = yield from self._get_multisend_tx(latest_vault)

                if multisend_data_obj != {}:
                    multisend_data_str = cast(str, multisend_data_obj["encoded"])
                    multisend_data = bytes.fromhex(multisend_data_str[2:])
                    tx_hash = yield from self._get_safe_hash(multisend_data)
                    multisend_data_obj["encoded"] = hash_payload_to_hex(
                        safe_tx_hash=tx_hash,
                        ether_value=0,
                        safe_tx_gas=10 ** 7,
                        operation=SafeOperation.DELEGATE_CALL.value,
                        to_address=self.params.multisend_address,
                        data=multisend_data,
                    )

            except AEAEnforceError as e:
                multisend_data_obj = {}
                self.context.logger.error(f"couldn't create transaction payload, e={e}")

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = PayoutFractionsPayload(
                self.context.agent_address,
                json.dumps(multisend_data_obj, sort_keys=True),
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
            to_address=self.params.multisend_address,
            value=0,
            data=data,
            safe_tx_gas=10 ** 7,
            operation=SafeOperation.DELEGATE_CALL.value,
        )

        enforce(
            response.state.body is not None
            and "tx_hash" in response.state.body.keys()
            and response.state.body["tx_hash"] is not None,
            "contract returned and empty body or empty tx_hash",
        )

        tx_hash = cast(str, response.state.body["tx_hash"])[2:]

        return tx_hash

    def _get_transferERC20_tx(
        self, address: str, amount: int
    ) -> Generator[None, None, str]:
        latest_vault = cast(List[str], self.period_state.db.get("vault_addresses"))[-1]

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_id=str(TokenVaultContract.contract_id),
            contract_callable="get_transfer_erc20_data",
            contract_address=latest_vault,
            receiver_address=address,
            amount=amount,
        )

        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        data = cast(str, response.state.body["data"])

        return data

    def _available_tokens(self) -> Generator:
        """Get the tokens that are left undistributed."""
        latest_vault = cast(List[str], self.period_state.db.get("vault_addresses"))[-1]
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_id=str(TokenVaultContract.contract_id),
            contract_callable="get_balance",
            contract_address=latest_vault,
            address=self.period_state.db.get("safe_contract_address"),
        )

        if (
            response.state.body is None
            or "balance" not in response.state.body.keys()
            or response.state.body["balance"] is None
        ):
            self.context.logger.error(
                "Could not retrieve the token balance of the safe contract."
            )
            return None

        return cast(int, response.state.body["balance"])

    def _get_unpaid_users(  # pylint: disable=too-many-locals
        self, wei_to_fractions: int
    ) -> Generator:
        """Get a dictionary of addresses and the tokens to be sent to them."""

        paid_users = cast(Dict[str, int], self.period_state.db.get("paid_users", {}))
        all_transfers = cast(
            List[Dict], self.period_state.db.get("most_voted_funds", [])
        )
        undistributed_tokens: Optional[int] = yield from self._available_tokens()
        tokens_to_be_distributed = 0
        address_to_investment: Dict = {}
        users_to_be_paid: Dict = {}

        if len(all_transfers) == 0 or undistributed_tokens is None:
            return {}

        for tx in all_transfers:
            sender, amount = tx["sender"], tx["amount"]

            if (
                sender
                in address_to_investment.keys()  # pylint: disable=consider-iterating-dictionary
            ):
                address_to_investment[sender] += amount
            else:
                address_to_investment[sender] = amount

        for address, invested_amount in address_to_investment.items():
            if tokens_to_be_distributed >= undistributed_tokens:
                self.context.logger.warning("No more tokens left!")
                break

            already_paid_amount = 0

            if address in paid_users.keys():
                already_paid_amount = paid_users[address] * wei_to_fractions

            unpaid_eth_amount = invested_amount - already_paid_amount
            owned_amount = unpaid_eth_amount // wei_to_fractions

            if owned_amount + tokens_to_be_distributed > undistributed_tokens:
                self.context.logger.warning(
                    "Not enough funds to payout all the owned tokens, they will be paid when the next vault is created!"
                )
                owned_amount = undistributed_tokens - tokens_to_be_distributed

            if owned_amount != 0:
                users_to_be_paid[address] = owned_amount
                tokens_to_be_distributed += owned_amount

        return users_to_be_paid

    def _get_multisend_tx(self, vault_address: str) -> Generator[None, None, JSONLike]:
        wei_to_fraction = self.params.wei_to_fraction
        unpaid_users = yield from self._get_unpaid_users(wei_to_fraction)
        erc20_txs = []

        if unpaid_users == {}:
            return {}

        for address, amount in unpaid_users.items():
            tx = yield from self._get_transferERC20_tx(address, amount)
            erc20_txs.append(
                {
                    "operation": MultiSendOperation.CALL,
                    "to": vault_address,
                    "value": 0,
                    "data": HexBytes(tx),
                }
            )

        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,  # type: ignore
            contract_address=self.params.multisend_address,
            contract_id=str(MultiSendContract.contract_id),
            contract_callable="get_tx_data",
            multi_send_txs=erc20_txs,
        )
        multisend_data = cast(str, contract_api_msg.raw_transaction.body["data"])

        self.context.logger.error(multisend_data)

        return {
            "encoded": multisend_data,
            "raw": unpaid_users,
        }


class PostPayoutRoundBehaviour(ElcollectooorrABCIBaseState):
    """Trivial behaviour for post payout"""

    state_id = "post_fraction_payout_behaviour"
    matching_round = PostPayoutRound

    def async_act(self) -> Generator:
        """Trivially log that the behaviour is done."""
        users_paid = self.period_state.db.get("users_being_paid", "{}")

        self.context.logger.info(f"The following users were paid: {users_paid}")
        yield from self.wait_until_round_end()

        self.set_done()


class PostFractionsPayoutRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Post Payout abci app."""

    initial_state_cls = PostPayoutRoundBehaviour
    abci_app_cls = PostFractionPayoutAbciApp
    behaviour_states: Set[Type[BaseState]] = {  # type: ignore
        PostPayoutRoundBehaviour,  # type: ignore
    }


class ProcessPurchaseRoundBehaviour(ElcollectooorrABCIBaseState):
    """Process the purchase of an NFT"""

    state_id = "process_purchase"
    matching_round = ProcessPurchaseRound

    def async_act(self) -> Generator:
        """Implement the act."""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            token_id = -1
            try:
                token_id = yield from self._get_token_id()
                self.context.logger.info(f"Purchased token id={token_id}.")
            except AEAEnforceError as e:
                self.context.logger.error(f"couldn't create transaction payload, e={e}")

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = PurchasedNFTPayload(
                self.context.agent_address,
                token_id,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_token_id(self) -> Generator[None, None, int]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="process_purchase_receipt",
            tx_hash=self.period_state.db.get("final_tx_hash"),
        )

        if response.state.body is None or "token_id" not in response.state.body.keys():
            self.context.logger.error(
                "couldn't extract the 'token_id' from the ArtBlocksContract"
            )

            return -1

        data = cast(int, response.state.body["token_id"])

        return data


class TransferNFTRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Transaction Round behaviour"""

    state_id = "transfer_nft"
    matching_round = TransferNFTRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            try:
                transfer_data_str = yield from self._get_safe_transfer_from_data()
                transfer_data = bytes.fromhex(transfer_data_str[2:])
                tx_hash = yield from self._get_safe_hash(transfer_data)

                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=0,
                    safe_tx_gas=10 ** 7,
                    to_address=self.params.artblocks_contract,
                    data=transfer_data,
                )

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create the transaction payload, e={e}"
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = TransferNFTPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, data: bytes) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.params.artblocks_contract,
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

    def _get_safe_transfer_from_data(self) -> Generator[None, None, str]:
        latest_basket = cast(List[str], self.period_state.db.get("basket_addresses"))[
            -1
        ]
        token_id = self.period_state.db.get("purchased_nft", None)

        if token_id is None:
            self.context.logger.info("No token to be transferred.")
            return ""

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="safe_transfer_from_data",
            from_address=self.period_state.db.get("safe_contract_address"),
            to_address=latest_basket,
            token_id=token_id,
        )

        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        data = cast(str, response.state.body["data"])

        return data


class TransferNFTAbciBehaviour(AbstractRoundBehaviour):
    """Behaviour class for the Transfer NFT Behaviour."""

    initial_state_cls = ProcessPurchaseRoundBehaviour
    abci_app_cls = TransferNFTAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        ProcessPurchaseRoundBehaviour,
        TransferNFTRoundBehaviour,
    }


class PostTransactionSettlementBehaviour(ElcollectooorrABCIBaseState):
    """Behaviour for Post TX Settlement Round."""

    matching_round = PostTransactionSettlementRound
    state_id = "post_tx_settlement_state"

    def async_act(self) -> Generator:
        """Simply log that the app was executed successfully."""
        payload_data = {}

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            try:
                tx_submitter = self.period_state.db.get("tx_submitter", None)

                if tx_submitter is None:
                    self.context.logger.error(
                        "A TX was settled, but the `tx_submitter` is unavailable!"
                    )
                else:
                    self.context.logger.info(
                        f"The TX submitted by {tx_submitter} was settled."
                    )

                amount_spent = yield from self._get_amount_spent()
                payload_data["amount_spent"] = amount_spent
                self.context.logger.info(
                    f"The settled tx cost: {amount_spent / 10 ** 18}Ξ."
                )

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create the PostTransactionSettlement payload, {type(e).__name__}: {e}."
                )

            with self.context.benchmark_tool.measure(
                self,
            ).consensus():
                payload = PostTxPayload(
                    self.context.agent_address,
                    json.dumps(payload_data),
                )

                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

            yield from self.wait_until_round_end()
            self.set_done()

    def _get_amount_spent(self) -> Generator[None, None, int]:
        """Get the amount of ether spent in the last settled tx."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address="0x0000000000000000000000000000000000000000",  # not needed
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_amount_spent",
            tx_hash=self.period_state.db.get("final_tx_hash"),
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and response.state.body["amount_spent"] is not None,
            "response, response.state, response.state.body must exist",
        )

        data = cast(int, response.state.body["amount_spent"])

        return data


class TransactionSettlementMultiplexerFullBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Tx Settlement Multiplexer abci app."""

    initial_state_cls = PostTransactionSettlementBehaviour
    abci_app_cls = TransactionSettlementAbciMultiplexer  # type: ignore
    behaviour_states: Set[Type[BaseState]] = {  # type: ignore
        PostTransactionSettlementBehaviour,  # type: ignore
    }


class ElCollectooorrRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El Collectooorr abci app."""

    initial_state_cls = ObservationRoundBehaviour
    abci_app_cls = ElcollectooorrBaseAbciApp  # type: ignore
    behaviour_states: Set[Type[BaseState]] = {  # type: ignore
        ObservationRoundBehaviour,  # type: ignore
        DetailsRoundBehaviour,  # type: ignore
        DecisionRoundBehaviour,  # type: ignore
        TransactionRoundBehaviour,  # type: ignore
    }


class BankRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Bank ABCI app."""

    initial_state_cls = FundingRoundBehaviour
    abci_app_cls = BankAbciApp
    behaviour_states: Set[Type[BaseState]] = {  # type: ignore
        FundingRoundBehaviour,  # type: ignore
        PayoutFractionsRoundBehaviour,  # type: ignore
    }


class ElCollectooorrFullRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El Collectooorr abci app."""

    initial_state_cls = RegistrationStartupBehaviour
    abci_app_cls = ElCollectooorrAbciApp  # type: ignore
    behaviour_states: Set[Type[BaseState]] = {
        *AgentRegistrationRoundBehaviour.behaviour_states,
        *SafeDeploymentRoundBehaviour.behaviour_states,
        *TransactionSettlementRoundBehaviour.behaviour_states,
        *ElCollectooorrRoundBehaviour.behaviour_states,
        *DeployVaultRoundBehaviour.behaviour_states,
        *DeployBasketRoundBehaviour.behaviour_states,
        *PostBasketDeploymentRoundBehaviour.behaviour_states,
        *PostVaultDeploymentRoundBehaviour.behaviour_states,
        *TransactionSettlementMultiplexerFullBehaviour.behaviour_states,
        *BankRoundBehaviour.behaviour_states,
        *PostFractionsPayoutRoundBehaviour.behaviour_states,
        *TransferNFTAbciBehaviour.behaviour_states,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger
