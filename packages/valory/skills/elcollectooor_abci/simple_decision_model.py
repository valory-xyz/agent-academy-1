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

"""This module provides a very simple decision algorithm for NFT selection on Art Blocks."""
import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
from aea.exceptions import enforce


_default_logger = logging.getLogger(__name__)


class DecisionModel:
    """Framework for any decision models."""

    def __init__(self) -> None:
        self.score = 0
        self.project_id: Optional[int] = None
        self.threshold = 25
        self.price_threshold = 500000000000000000
        self.cancel_threshold = 10000
        self.TIOLI_threshold = 10
        self.dutch_threshold = 150
        self.logger = _default_logger

    def static(self, project_details: Dict) -> int:
        """First filtering of viable projects."""
        enforce(type(project_details) == dict, "Wrong data format of project details.")

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

    def dynamic(self, most_voted_details: Dict) -> int:
        """Automatic participation in the auction and optimal price discovery."""
        # TODO: define get more details

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

            elif price_per_token_in_wei > self.price_threshold:
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
