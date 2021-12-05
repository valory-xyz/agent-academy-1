from collections import Generator
from typing import Optional, Any, cast

from packages.valory.contracts.artblocks_periphery.contract import ArtBlocksPeripheryContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviour_utils import AsyncBehaviour
from packages.valory.skills.elcollectooor_abci.behaviours import ElCollectooorABCIBaseState, benchmark_tool
from packages.valory.skills.elcollectooor_abci.payloads import ObservationPayload
from packages.valory.skills.elcollectooor_abci.rounds import ObservationRound


class ObservationRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "observation"
    matching_round = ObservationRound

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
        # TODO: define retry mechanism

        with benchmark_tool.measure(
                self,
        ).local():
            # fetch an active project
            response = yield from self._send_contract_api_request(
                request_callback=self._handle_active_project_id,  # TODO: can default_callback do the job?
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=self.artblocks_periphery_contract,
                contract_id=str(ArtBlocksPeripheryContract.contract_id),
                contract_callable="get_active_project",
                starting_id=self.starting_id,
            )

            # response body also has project details
            project_details = response.state.body
            project_id = project_details["project_id"]

        if project_id:
            self.context.logger.info(f"Retrieved project id: {project_id}.")
            payload = ObservationPayload(
                self.context.agent_address,
                project_details,
            )

            with benchmark_tool.measure(
                    self,
            ).consensus():
                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

    def _handle_active_project_id(self, message: ContractApiMessage) -> None:
        """Callback handler for the active project id request."""
        # TODO: maybe move it to the base class and use it as the default callback

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
