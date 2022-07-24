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
from packages.valory.contracts.artblocks_minter_filter.contract import (
    ArtBlocksMinterFilterContract,
)
from packages.valory.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.valory.contracts.basket_factory.contract import BasketFactoryContract
from packages.valory.contracts.gnosis_safe.contract import (
    GnosisSafeContract,
    SafeOperation,
)
from packages.valory.contracts.multisend.contract import (
    MultiSendContract,
    MultiSendOperation,
)
from packages.valory.contracts.token_vault.contract import TokenVaultContract
from packages.valory.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviours import AbstractRoundBehaviour
from packages.valory.skills.abstract_round_abci.behaviours import (
    BaseBehaviour as BaseState,
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
    ResyncPayload,
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
    ResyncAbciApp,
    ResyncRound,
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
        return cast(
            PeriodState, cast(SharedState, self.context.state).synchronized_data
        )

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class ResyncRoundBehaviour(
    ElcollectooorrABCIBaseState
):  # pylint: disable=too-many-locals, too-many-statements
    """Behaviour for the resyncing round."""

    behaviour_id = "resync"
    matching_round = ResyncRound

    def async_act(self) -> Generator:
        """The resyncing act."""
        with self.context.benchmark_tool.measure(
            self,
        ).local():
            payload_data = {}
            try:
                safe_txs = yield from self._get_safe_txs()
                block_nums = [tx["block_number"] for tx in safe_txs]
                earliest_tx, latest_tx = (
                    min(block_nums),
                    max(block_nums),
                )  # these will help in filtering events
                self.context.logger.info(f"found safe txs: {safe_txs}")
                self.context.logger.info(
                    f"earliest tx block num: {earliest_tx}; latest tx block num: {latest_tx}"
                )

                all_mints = yield from self._get_all_mints(
                    from_block=earliest_tx, to_block=latest_tx
                )
                curated_projects = yield from self._get_curated_projects()
                purchased_project_ids = [mint["project_id"] for mint in all_mints]
                purchased_projects = [
                    dict(
                        project_id=project_id,
                        is_curated=(project_id in curated_projects),
                    )
                    for project_id in purchased_project_ids
                ]
                self.context.logger.info(
                    f"already purchased projects: {purchased_project_ids}"
                )

                baskets = yield from self._get_all_baskets(
                    from_block=earliest_tx, to_block=latest_tx
                )
                basket_addresses: List[str] = []
                vault_addresses: List[str] = []
                latest_basket: str
                latest_vault: str
                # defines the block in which the most recent basket was deployed to
                max_block_num = 0
                for basket in baskets:
                    basket_address = basket["basket_address"]
                    block_num = basket["block_number"]
                    basket_addresses.append(basket_address)

                    vault = yield from self._get_vault(
                        basket_address,
                        from_block=block_num,
                        to_block=(
                            block_num + 50
                        ),  # we give a 50 block window for the vault to be deployed after the basket
                    )
                    vault_addresses += vault

                    if len(vault) == 0:
                        self.context.logger.warning(
                            f"basket {basket_address} is not associated with any vault."
                        )
                    elif len(vault) > 1:
                        self.context.logger.warning(
                            f"basket {basket_address} is associated with {len(vault)} vaults"
                        )

                    if block_num > max_block_num:
                        max_block_num = block_num
                        latest_basket = basket_address
                        # we take the first in case the basket-to-vault relation is 1:n.
                        # NOTE: we expect it to be 1:1, under certain conditions it can be 1:0.
                        # example: the service is down just after a basket is deployed but before
                        # a vault is deployed.
                        if len(vault) > 0:
                            latest_vault = vault[0]

                self.context.logger.info(f"all deployed baskets: {basket_addresses}")
                self.context.logger.info(f"latest deployed basket: {latest_basket}")
                self.context.logger.info(f"all deployed vaults: {vault_addresses}")
                self.context.logger.info(f"latest deployed vault: {latest_vault}")

                all_payouts = []
                for vault_address in vault_addresses:
                    payouts = yield from self._get_payouts(
                        vault_address, from_block=earliest_tx, to_block=latest_tx
                    )
                    all_payouts.extend(payouts)

                txs_since_last_basket = [
                    tx["tx_hash"]
                    for tx in safe_txs
                    if tx["block_number"] >= max_block_num
                ]
                amount_spent = yield from self._get_amount_spent(txs_since_last_basket)
                address_to_fractions = self._address_to_fractions(all_payouts)
                self.context.logger.info(
                    f"txs since the deployment of the last basket: {txs_since_last_basket}"
                )
                self.context.logger.info(
                    f"amount spent since last basket was deployed: {amount_spent / 10 ** 18}Ξ"
                )
                self.context.logger.info(
                    f"address to fraction amount already paid out: {address_to_fractions}"
                )
                payload_data = {
                    "amount_spent": amount_spent,
                    "basket_addresses": [latest_basket] if latest_basket else [],
                    "vault_addresses": [latest_vault] if latest_vault else [],
                    "purchased_projects": purchased_projects,
                    "paid_users": address_to_fractions,
                }
            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't resync, the following error was encountered {type(e).__name__}: {e}"
                )

            with self.context.benchmark_tool.measure(
                self,
            ).consensus():
                payload = ResyncPayload(
                    self.context.agent_address,
                    json.dumps(payload_data),
                )

                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

        self.set_done()

    @staticmethod
    def _address_to_fractions(all_payouts: List[Dict]) -> Dict[str, int]:
        """Organize payouts by the receiving address."""
        addr_to_fractions: Dict[str, int] = {}

        for payout in all_payouts:
            address, value = payout["to"], payout["value"]
            if address not in addr_to_fractions.keys():
                addr_to_fractions[address] = 0

            addr_to_fractions[address] = addr_to_fractions[address] + value

        return addr_to_fractions

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

    def _get_safe_txs(
        self,
    ) -> Generator[None, None, List[Dict]]:
        """Get the all MultiSig txs made by the safe."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.period_state.db.get_strict("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_safe_txs",
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "txs" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        return cast(List[Dict], response.state.body["txs"])

    def _get_payouts(
        self, vault_address: str, from_block: Optional[int], to_block: Optional[int]
    ) -> Generator[None, None, List]:
        """Get all fractions payouts for all investors."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=vault_address,
            from_address=self.period_state.db.get_strict("safe_contract_address"),
            contract_id=str(TokenVaultContract.contract_id),
            contract_callable="get_all_erc20_transfers",
            from_block=from_block,
            to_block=to_block,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "payouts" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        return cast(List[Dict], response.state.body["payouts"])

    def _get_all_baskets(
        self, from_block: Optional[int], to_block: Optional[int]
    ) -> Generator[None, None, List[Dict]]:
        """Get all deployed baskets."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.basket_factory_address,
            contract_id=str(BasketFactoryContract.contract_id),
            contract_callable="get_deployed_baskets",
            deployer_address=self.period_state.db.get_strict("safe_contract_address"),
            from_block=from_block,
            to_block=to_block,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "baskets" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        return cast(List[Dict], response.state.body["baskets"])

    def _get_vault(
        self, basket_address: str, from_block: Optional[int], to_block: Optional[int]
    ) -> Generator[None, None, List[str]]:
        """Get deployed vault with the basket."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.token_vault_factory_address,
            token_address=basket_address,
            contract_id=str(TokenVaultFactoryContract.contract_id),
            contract_callable="get_deployed_vaults",
            from_block=from_block,
            to_block=to_block,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "vaults" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        return cast(List[str], response.state.body["vaults"])

    def _get_all_mints(
        self, from_block: Optional[int], to_block: Optional[int]
    ) -> Generator[None, None, List[Dict]]:
        """Get all purchased projects and tokens by the agent."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            minted_to_address=self.period_state.db.get_strict("safe_contract_address"),
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="get_mints",
            from_block=from_block,
            to_block=to_block,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "mints" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        return cast(List[Dict], response.state.body["mints"])

    def _get_amount_spent(
        self,
        txs: List[str],
    ) -> Generator[None, None, int]:
        """Get the amount of wei spent in the provided txs."""
        total_amount_spent = 0
        for tx in txs:
            response = yield from self.get_contract_api_response(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x0000000000000000000000000000000000000000",  # not needed
                contract_id=str(GnosisSafeContract.contract_id),
                contract_callable="get_amount_spent",
                tx_hash=tx,
            )

            enforce(
                response is not None
                and response.state is not None
                and response.state.body is not None
                and "amount_spent" in response.state.body.keys()
                and response.state.body["amount_spent"] is not None,
                "response, response.state, response.state.body must exist",
            )

            tx_cost = cast(int, response.state.body["amount_spent"])
            total_amount_spent += tx_cost

        return total_amount_spent


class ObservationRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Observation round behaviour"""

    behaviour_id = "observation"
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

    behaviour_id = "details"
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
        all_project_details: Dict[str, Dict] = {}
        minter_to_projects: Dict[str, List] = {}
        curated_projects = yield from self._get_curated_projects()
        project_to_minters = yield from self._project_minter(projects)

        for project_id, project in project_to_minters.items():
            minter = project["minter_for_project"]

            if minter not in minter_to_projects.keys():
                minter_to_projects[minter] = []

            minter_to_projects[minter].append(project_id)

        for minter, projects_in_minter in minter_to_projects.items():
            if minter == "0x":
                continue

            project_details = yield from self._project_details(
                projects_in_minter, minter
            )
            all_project_details.update(project_details)

        for project in projects:
            project_id = project["project_id"]

            if project_id not in all_project_details:
                # the project might not be assigned a minter
                continue

            project_details = all_project_details[project_id]
            project_minter = project_to_minters[project_id]

            project["is_mintable_via_contract"] = project_details[
                "is_mintable_via_contract"
            ]
            project["is_price_configured"] = project_details["is_price_configured"]
            project["price"] = project_details[
                "price_per_token_in_wei"
            ]  # this price always supersedes this core price
            project["currency_symbol"] = project_details["currency_symbol"]
            project["currency_address"] = project_details["currency_address"]
            project["is_curated"] = project_id in curated_projects
            project["minter"] = project_minter["minter_for_project"]

            enhanced_projects.append(project)

        return enhanced_projects

    def _project_details(
        self, project_ids: List[int], minter_address: str
    ) -> Generator[None, None, Dict]:
        """Get the details of all the active projects."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=minter_address,
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            contract_callable="get_multiple_project_details",
            project_ids=project_ids,
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None,
            "response, response.state, response.state.body must exist",
        )

        details = cast(Dict, response.state.body)

        enforce(
            len(details) == len(project_ids),
            "Invalid response was received from 'get_multiple_project_details'.",
        )

        return details

    def _project_minter(self, projects: List[Dict]) -> Generator[None, None, Dict]:
        """Get the minter of all the active projects."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_minter_filter,
            contract_id=str(ArtBlocksMinterFilterContract.contract_id),
            contract_callable="get_multiple_projects_minter",
            project_ids=[p["project_id"] for p in projects],
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None,
            "response, response.state, response.state.body must exist",
        )

        details = cast(Dict, response.state.body)

        enforce(
            len(details) == len(projects),
            "Invalid response was received from 'get_multiple_projects_minter'.",
        )

        return details

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

    behaviour_id = "decision"
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
            contract_address=self.period_state.db.get_strict("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_balance",
        )

        enforce(
            response is not None
            and response.state is not None
            and response.state.body is not None
            and "balance" in response.state.body.keys(),
            "response, response.state, response.state.body must exist",
        )

        return cast(int, response.state.body["balance"])


class TransactionRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Transaction Round behaviour"""

    behaviour_id = "transaction_collection"
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
                minter = project_to_purchase["minter"]
                value = project_to_purchase[
                    "price"
                ]  # price of token in the project in wei
                purchase_data_str = yield from self._get_purchase_data(
                    project_to_purchase["project_id"],
                    minter,
                )
                purchase_data = bytes.fromhex(purchase_data_str[2:])
                tx_hash = yield from self._get_safe_hash(
                    data=purchase_data,
                    value=value,
                    to_address=minter,
                )
                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=value,
                    safe_tx_gas=10 ** 7,
                    to_address=minter,
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

    def _get_safe_hash(
        self, to_address: str, data: bytes, value: int = 0
    ) -> Generator[None, None, str]:
        """Get the safe hash."""

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.db.get_strict("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=to_address,
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

    def _get_purchase_data(
        self, project_id: int, minter: str
    ) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=minter,
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

    behaviour_id = "funding_behaviour"
    matching_round = FundingRound

    def async_act(self) -> Generator:
        """Get the available funds and store them to state."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            available_funds = []
            try:
                in_transfers = yield from self._get_in_transfers()
                available_funds = self._get_available_funds(in_transfers)
            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't get transfers to the safe contract, "
                    f"the following error was encountered {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            payload = FundingPayload(
                self.context.agent_address,
                address_to_funds=json.dumps(available_funds),
            )
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_in_transfers(
        self, from_block: Optional[int] = None, to_block: Union[str, int] = "latest"
    ) -> Generator[None, None, List[Dict]]:
        """Returns all the transfers to the gnosis safe."""

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.period_state.db.get("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_ingoing_transfers",
            from_block=from_block,
            to_block=to_block,
        )

        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        return cast(List[Dict], response.state.body["data"])

    def _get_available_funds(self, in_transfers: List[Dict]) -> List[Dict]:
        """Get funds that are available for use."""
        self.context.logger.info(
            f"Investor whitelisting is active? {self.params.enforce_investor_whitelisting}"
        )

        if self.params.enforce_investor_whitelisting:
            filtered_transfers = list(
                filter(
                    lambda transfer: transfer["sender"]
                    in self.params.whitelisted_investor_addresses,
                    in_transfers,
                )
            )

            self.context.logger.info(
                f"{len(filtered_transfers)} transfers from whitelisted investors."
            )
            self.context.logger.info(
                f"{len(in_transfers) - len(filtered_transfers)} transfers from non-whitelisted investors."
            )

            return filtered_transfers

        return in_transfers


class PayoutFractionsRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the DeployBasketTxRoundRound behaviour"""

    behaviour_id = "payout_fractions"
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
                self.context.logger.error(
                    f"Couldn't create PayoutFractions payload, "
                    f"the following error was encountered {type(e).__name__}: {e}"
                )

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

        enforce(
            response.state.body is not None
            and "balance" in response.state.body.keys()
            and response.state.body["balance"] is not None,
            "Could not retrieve the token balance of the safe contract.",
        )

        return cast(int, response.state.body["balance"])

    def _get_unpaid_users(  # pylint: disable=too-many-locals
        self, wei_to_fractions: int
    ) -> Generator:
        """Get a dictionary of addresses and the tokens to be sent to them."""

        paid_users = cast(Dict[str, int], self.period_state.db.get("paid_users", {}))
        all_transfers = cast(
            List[Dict], self.period_state.db.get("most_voted_funds", [])
        )
        undistributed_tokens = yield from self._available_tokens()
        tokens_to_be_distributed = 0
        address_to_investment: Dict = {}
        users_to_be_paid: Dict = {}

        if len(all_transfers) == 0 or undistributed_tokens is None:
            return {}

        undistributed_tokens = cast(int, undistributed_tokens)

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

        if unpaid_users == {} or unpaid_users is None:
            return {}

        unpaid_users = cast(Dict, unpaid_users)

        self.context.logger.info(
            f"{len(unpaid_users)} user(s) is(are) getting paid their fractions."
        )

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

    behaviour_id = "post_fraction_payout_behaviour"
    matching_round = PostPayoutRound

    def async_act(self) -> Generator:
        """Trivially log that the behaviour is done."""
        users_paid = self.period_state.db.get("users_being_paid", "{}")

        self.context.logger.info(f"The following users were paid: {users_paid}")
        yield from self.wait_until_round_end()

        self.set_done()


class PostFractionsPayoutRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Post Payout abci app."""

    initial_behaviour_cls = PostPayoutRoundBehaviour
    abci_app_cls = PostFractionPayoutAbciApp
    behaviours: Set[Type[BaseState]] = {  # type: ignore
        PostPayoutRoundBehaviour,  # type: ignore
    }


class ProcessPurchaseRoundBehaviour(ElcollectooorrABCIBaseState):
    """Process the purchase of an NFT"""

    behaviour_id = "process_purchase"
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
                self.context.logger.error(
                    f"Couldn't create PurchasedNFTPayload payload, "
                    f"the following error was encountered {type(e).__name__}: {e}"
                )

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

        enforce(
            response.state.body is not None
            and "token_id" in response.state.body.keys(),
            "Couldn't get token_id from the purchase tx hash.",
        )

        data = cast(int, response.state.body["token_id"])

        return data


class TransferNFTRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Transaction Round behaviour"""

    behaviour_id = "transfer_nft"
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
                    f"Couldn't create TransferNFT payload, "
                    f"the following error was encountered {type(e).__name__}: {e}."
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
            contract_address=self.period_state.db.get_strict("safe_contract_address"),
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

        enforce(token_id is not None, "No token to be transferred")
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

    initial_behaviour_cls = ProcessPurchaseRoundBehaviour
    abci_app_cls = TransferNFTAbciApp
    behaviours: Set[Type[BaseState]] = {
        ProcessPurchaseRoundBehaviour,
        TransferNFTRoundBehaviour,
    }


class PostTransactionSettlementBehaviour(ElcollectooorrABCIBaseState):
    """Behaviour for Post TX Settlement Round."""

    matching_round = PostTransactionSettlementRound
    behaviour_id = "post_tx_settlement_state"

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
                    f"Couldn't create the PostTransactionSettlement payload, "
                    f"the following error was encountered {type(e).__name__}: {e}."
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
            and "amount_spent" in response.state.body.keys()
            and response.state.body["amount_spent"] is not None,
            "response, response.state, response.state.body must exist",
        )

        data = cast(int, response.state.body["amount_spent"])

        return data


class TransactionSettlementMultiplexerFullBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Tx Settlement Multiplexer abci app."""

    initial_behaviour_cls = PostTransactionSettlementBehaviour
    abci_app_cls = TransactionSettlementAbciMultiplexer  # type: ignore
    behaviours: Set[Type[BaseState]] = {  # type: ignore
        PostTransactionSettlementBehaviour,  # type: ignore
    }


class ElCollectooorrRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El Collectooorr abci app."""

    initial_behaviour_cls = ObservationRoundBehaviour
    abci_app_cls = ElcollectooorrBaseAbciApp  # type: ignore
    behaviours: Set[Type[BaseState]] = {  # type: ignore
        ObservationRoundBehaviour,  # type: ignore
        DetailsRoundBehaviour,  # type: ignore
        DecisionRoundBehaviour,  # type: ignore
        TransactionRoundBehaviour,  # type: ignore
    }


class BankRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Bank ABCI app."""

    initial_behaviour_cls = FundingRoundBehaviour
    abci_app_cls = BankAbciApp
    behaviours: Set[Type[BaseState]] = {  # type: ignore
        FundingRoundBehaviour,  # type: ignore
        PayoutFractionsRoundBehaviour,  # type: ignore
    }


class ResyncAbciBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the Bank ABCI app."""

    initial_behaviour_cls = ResyncRoundBehaviour
    abci_app_cls = ResyncAbciApp
    behaviours: Set[Type[BaseState]] = {  # type: ignore
        ResyncRoundBehaviour,  # type: ignore
    }


class ElCollectooorrFullRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El Collectooorr abci app."""

    initial_behaviour_cls = RegistrationStartupBehaviour
    abci_app_cls = ElCollectooorrAbciApp  # type: ignore
    behaviours: Set[Type[BaseState]] = {
        *AgentRegistrationRoundBehaviour.behaviours,
        *SafeDeploymentRoundBehaviour.behaviours,
        *TransactionSettlementRoundBehaviour.behaviours,
        *ElCollectooorrRoundBehaviour.behaviours,
        *DeployVaultRoundBehaviour.behaviours,
        *DeployBasketRoundBehaviour.behaviours,
        *PostBasketDeploymentRoundBehaviour.behaviours,
        *PostVaultDeploymentRoundBehaviour.behaviours,
        *TransactionSettlementMultiplexerFullBehaviour.behaviours,
        *BankRoundBehaviour.behaviours,
        *PostFractionsPayoutRoundBehaviour.behaviours,
        *TransferNFTAbciBehaviour.behaviours,
        *ResyncAbciBehaviour.behaviours,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger
