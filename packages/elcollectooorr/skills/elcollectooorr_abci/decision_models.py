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


class EightyPercentDecisionModel(ABC):  # pylint: disable=too-few-public-methods
    """Decision model that purchases only 80% minted projects."""

    @staticmethod
    def decide(
        active_projects: List[dict],
        purchased_projects: List[dict],
        budget: int,
        max_purchase_per_project: int,
        decision_threshold: float,
    ) -> List[Dict]:
        """
        Method to decide on what projects to purchase.

        :param active_projects: projects that are currently active.
        :param purchased_projects: projects that have been purchased.
        :param budget: the available budget in wei.
        :param max_purchase_per_project: defines the maximum times a project can be purchased.
        :param decision_threshold: defines the minimum minted percentage a project needs to have to be considered.
        :return: an ordered list of projects, based on "fitness" to purchase.
        """
        purchased_curated = [p for p in purchased_projects if p["is_curated"]]
        purchased_non_curated = [p for p in purchased_projects if not p["is_curated"]]
        purchased_project_ids = [p["project_id"] for p in purchased_projects]
        # only purchase non-curated if there are more curated than non-curated
        can_purchase_non_curated = len(purchased_curated) > len(purchased_non_curated)
        potential_projects = []

        for project in active_projects:
            if project["minted_percentage"] < decision_threshold:
                _default_logger.info(
                    f"Project #{project['project_id']} doesnt meet the minting threshold, "
                    f"we require {decision_threshold} "
                    f"but project #{project['project_id']} is at {project['minted_percentage']}"
                )
                continue

            if not project["is_mintable_via_contract"]:
                _default_logger.info(
                    f"Project #{project['project_id']} cannot be purchased via contracts, "
                    f"and purchasing via EOAs is disabled."
                )
                continue

            if project["currency_symbol"] != "ETH":
                _default_logger.info(
                    f"Project #{project['project_id']} cannot be purchased with ETH."
                )
                continue

            if not project["is_price_configured"]:
                _default_logger.info(
                    f"Project #{project['project_id']} doesnt have a price configured."
                )
                continue

            if (
                purchased_project_ids.count(project["project_id"])
                >= max_purchase_per_project
            ):
                _default_logger.info(
                    f"Project #{project['project_id']} is already purchased."
                )
                continue

            if project["price"] > budget:
                _default_logger.info(
                    f"Project #{project['project_id']} is too expensive."
                )
                continue

            if not project["is_curated"] and not can_purchase_non_curated:
                _default_logger.info(
                    f"Project #{project['project_id']} is non-curated, but we need to purchase a curated project."
                )
                continue

            _default_logger.info(
                f"Project #{project['project_id']} is a project we can purchase."
            )

            potential_projects.append(project)

        potential_projects.sort(key=lambda p: p["minted_percentage"], reverse=True)

        return potential_projects


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
        :return: the decision 0=No, 1=Yes
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
            ma_blocks = ret[10 - 1 :] / 10

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
