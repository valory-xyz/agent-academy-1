from collections import Generator
from typing import Any

from packages.valory.contracts.artblocks_periphery.contract import ArtBlocksPeripheryContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviour_utils import AsyncBehaviour
from packages.valory.skills.elcollectooor_abci.behaviours import ElCollectooorABCIBaseState, benchmark_tool
from packages.valory.skills.elcollectooor_abci.payloads import TransactionPayload
from packages.valory.skills.elcollectooor_abci.rounds import TransactionCollectionRound, TransactionSendingRound


class TransactionCollectionRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "transaction_collection"
    matching_round = TransactionCollectionRound

    def async_act(self) -> Generator:
        """Implement the act."""
        with benchmark_tool.measure(
                self,
        ).local():
            # fetch an active project
            signed_tx = self._generate_tx()

            payload = TransactionPayload(
                self.context.agent_address,
                signed_tx,
            )

            with benchmark_tool.measure(
                    self,
            ).consensus():
                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

    def _generate_tx(self):
        return "base64_tx"


class TransactionSendingRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "transaction_collection"
    matching_round = TransactionSendingRound

    def __init__(self, *args: Any, **kwargs: Any):
        """Init the observing behaviour."""
        super().__init__(**kwargs)
        # TODO: not all vars are necessary
        self.max_eth_in_wei = kwargs.pop("max_eth_in_wei", 1000000000000000000)
        self.safe_tx_gas = kwargs.pop("safe_tx_gas", 4000000)
        self.artblocks_contract = kwargs.pop(
            "artblocks_contract", "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
        )
        self.artblocks_periphery_contract = kwargs.pop(
            "artblocks_periphery_contract", "0x58727f5Fc3705C30C9aDC2bcCC787AB2BA24c441"
        )
        self.safe_contract = kwargs.pop(
            "safe_contract", "0x2caB92c1E9D2a701Ca0411b0ff35A0907Ca31F7f"
        )
        self.seconds_between_periods = kwargs.pop("seconds_between_periods", 30)
        self.starting_id = kwargs.pop("starting_id", 0)

    def async_act(self) -> Generator:
        """Implement the act."""
        with benchmark_tool.measure(
                self,
        ).local():
            response = yield from self._send_contract_api_request(
                request_callback=self._handle_purchase_data,
                performative=ContractApiMessage.Performative.GET_STATE,
                # TODO: should this transaction be made through the safe contract?
                contract_address=self.artblocks_periphery_contract,
                contract_id=str(ArtBlocksPeripheryContract.contract_id),
                contract_callable="purchase_data",
                project_id=self.period_state.most_voted_project["project_id"],
            )

        self.period_state.update(purchase_data_tx=response)

        yield from self.wait_until_round_end()

    def _handle_purchase_data(self, message: ContractApiMessage) -> None:
        # TODO: should be made generic?
        if not message.performative == ContractApiMessage.Performative.STATE:
            raise ValueError("wrong performative")

        if self.is_stopped:
            self.context.logger.debug(
                "dropping message as behaviour has stopped: %s", message
            )
        elif self.state == AsyncBehaviour.AsyncState.WAITING_MESSAGE:
            self.try_send(message)
        else:
            self.context.logger.warning(
                "could not send message to FSMBehaviour: %s", message
            )
