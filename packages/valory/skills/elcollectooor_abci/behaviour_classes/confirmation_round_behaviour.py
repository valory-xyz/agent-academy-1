from collections import Generator

from packages.valory.skills.elcollectooor_abci.behaviours import ElCollectooorABCIBaseState
from packages.valory.skills.elcollectooor_abci.rounds import ConfirmationRound


class ConfirmationRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "confirmation"
    matching_round = ConfirmationRound

    def async_act(self) -> Generator:
        pass
