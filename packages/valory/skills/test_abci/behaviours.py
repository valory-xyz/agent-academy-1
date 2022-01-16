# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021 Valory AG
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

"""This module contains the behaviours for the 'test_abci' skill."""

from abc import ABC
from math import floor
from typing import Generator, List, Set, Type

from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.abstract_round_abci.utils import BenchmarkTool
from packages.valory.skills.test_abci.rounds import (
    DummyRound,
    TestAbciApp,
)


def random_selection(elements: List[str], randomness: float) -> str:
    """
    Select a random element from a list.

    :param: elements: a list of elements to choose among
    :param: randomness: a random number in the [0,1) interval
    :return: a randomly chosen element
    """
    random_position = floor(randomness * len(elements))
    return elements[random_position]


benchmark_tool = BenchmarkTool()


class DummyBehaviour(BaseState, ABC):
    """Check whether Tendermint nodes are running."""

    state_id = "dummy"
    matching_round = DummyRound

    def async_act(self) -> Generator:
        """Do the action."""
        yield self.set_done()


class TestAbciConsensusBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the simple abci app."""

    initial_state_cls = DummyBehaviour
    abci_app_cls = TestAbciApp  # type: ignore
    behaviour_states: Set[Type[DummyBehaviour]] = {  # type: ignore
        DummyBehaviour,  # type: ignore
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        benchmark_tool.logger = self.context.logger
