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

"""This module provides a very simple decision algorithm for NFT selection on Art Blocks."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np
import pandas as pd  # type: ignore
from aea.exceptions import enforce

_default_logger = logging.getLogger(__name__)


class BaseDecisionModel(ABC):
    """Framework for any decision models."""

    @abstractmethod
    def static(self, project_details: Dict) -> int:
        """
        Initial filtering of viable projects.

        :param project_details: a dictionary with the static project_details
        :return: the decision 0=No, 1=Yes
        """

    @abstractmethod
    def dynamic(self, most_voted_details: List[Dict]) -> int:
        """
        Automatic participation in the auction and optimal price discovery.

        :param most_voted_details: a list of changing attributes over time
        :return: the decision 0=No, 1=Yes, -1=GIB DETAILS
        """


class SimpleDecisionModel(BaseDecisionModel):
    """A decision model that decides on a project by looking at multiple static and dynamic attrs of a project."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self) -> None:
        """Initializes a DecisionModel instance"""

        self.score = 0
        self.project_id: Optional[int] = None
        self.threshold = 25
        self.price_threshold = 500000000000000000
        self.cancel_threshold = 10000
        self.TIOLI_threshold = 10
        self.dutch_threshold = 150
        self.logger = _default_logger

    def static(self, project_details: Dict) -> int:
        """
        Initial filtering of viable projects.

        :param project_details: a dictionary with the static project_details
        :return: the decision 0=No, 1=Yes
        """
        enforce(
            isinstance(project_details, dict), "Wrong data format of project details."
        )

        if (
                not project_details["royalty_receiver"]
                    == "0x0000000000000000000000000000000000000000"
        ):
            self.score += 1
        if not project_details["description"] == "":
            self.score += 1
        if self.score >= 1:
            return 1
        return 0

    def dynamic(self, most_voted_details: List[Dict]) -> int:
        """
        Automatic participation in the auction and optimal price discovery.

        :param most_voted_details: a list of changing attributes over time
        :return: the decision 0=No, 1=Yes, -1=Not enough details
        """

        price_per_token_in_wei = most_voted_details[-1]["price_per_token_in_wei"]
        series = pd.DataFrame(most_voted_details).values

        if series.shape[0] > 10:
            avg_mints = np.mean(series[-10:-1, 1])
        else:
            avg_mints = np.mean(series[:, 1])

        blocks_to_go = (
                               most_voted_details[-1]["max_invocations"]
                               - most_voted_details[-1]["invocations"]
                       ) / (avg_mints + 0.001)

        if series.shape[0] > self.dutch_threshold and series[0, 0] == series[-1, 0]:
            self.logger.info("This is no Dutch auction.")
            # Moving Average of "blocks_to_go", window = 10
            ret = np.cumsum(np.diff(series[:, 1]), dtype=float)
            ret[10:] = ret[10:] - ret[:-10]
            ma_blocks = ret[10 - 1:] / 10

            if (
                    np.sum(ma_blocks[-20:] > 0) > self.TIOLI_threshold
                    and price_per_token_in_wei < self.price_threshold
            ):
                return 1

            if price_per_token_in_wei > self.price_threshold:
                return 0

        if (
                blocks_to_go
                < self.threshold + (100 / most_voted_details[-1]["max_invocations"])
                and price_per_token_in_wei < self.price_threshold
        ):
            self.logger.info("This is a Dutch auction or something very fast.")
            return 1

        if series.shape[0] > 1000 and blocks_to_go > self.cancel_threshold:
            return 0

        return -1


class EightyPercentDecisionModel(BaseDecisionModel):
    """Decision model that purchases when a project is 80% sold."""

    state = {
        "purchased_curated": False
    }

    def __init__(self, state: Dict):
        """
        Initialize the algorithm with an external state.

        :param state: The external (persisted) state.
        """
        self.state.update(state)

    def static(self, project_details: Dict) -> int:
        """"""
        is_curated = project_details["is_curated"]
        purchased_curated = self.state["purchased_curated"]

        if is_curated:
            # if it is curated, we will consider it
            return 1

        if not is_curated and purchased_curated:
            # if its not a curated projects, but we've purchase a curated proj we consider it
            return 1

        return 0


class YesDecisionModel(BaseDecisionModel):
    """Decision model that always decides to buy"""

    def static(self, project_details: Dict) -> int:
        """
        Decide for yes

        :param project_details: a dictionary with the static project_details
        :return: 1=Yes
        """
        return 1

    def dynamic(self, most_voted_details: List[Dict]) -> int:
        """
        Decide for yes

        :param most_voted_details: a list of changing attributes over time
        :return: 1=Yes
        """
        return 1


class NoDecisionModel(BaseDecisionModel):
    """A model that always decides to not buy a project"""

    def static(self, project_details: Dict) -> int:
        """
        Decide for no

        :param project_details: a dictionary with the static project_details
        :return: 0=No
        """
        return 0

    def dynamic(self, most_voted_details: List[Dict]) -> int:
        """
        Decide for no

        :param most_voted_details: a list of changing attributes over time
        :return: 0=No
        """
        return 0


class GibDetailsThenYesDecisionModel(YesDecisionModel):
    """A model that initially asks for more details, then decides for yes."""

    def dynamic(self, most_voted_details: List[Dict]) -> int:
        """
        Decide for yes if details are provided, otherwise decide for "GIB DETAILS"

        :param most_voted_details: a list of changing attributes over time
        :return: 1=Yes, -1=GIB DETAILS
        """

        if len(most_voted_details) > 1:
            return 1

        return -1
