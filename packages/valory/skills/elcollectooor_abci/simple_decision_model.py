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

from typing import Optional

import numpy as np


class DecisionModel:
    """Framework for any decision models."""

    def __init__(self):
        self.score = 0
        self.project_id: Optional[int] = None
        self.threshold = 25
        self.price_threshold = 500000000000000000
        self.cancel_threshold = 10000
        self.TIOLI_threshold = 7
        self.project_done = False

    def static(self, project_details):
        """First filtering of viable projects."""
        if not project_details["royalty_receiver"] == '0x0000000000000000000000000000000000000000':
            self.score += 1
        if not project_details["description"] == '':
            self.score += 1
        if self.score >= 1:
            return 1
        return 0

    def dynamic(self, project_details):
        """Automatic participation in the auction and optimal price discovery."""
        # TODO: define get more details
        i = 0
        series = np.array([])
        blocks_to_go = 10000000
        while not self.project_done:
            price_per_token_in_wei = project_details["price_per_token_in_wei"]
            progress = project_details["invocations"] / project_details["max_invocations"]
            series = np.append(series, (price_per_token_in_wei, progress, blocks_to_go)).reshape(-1, 3)

            if i > 10:
                avg_mints = np.mean(series[i - 10:i, 1] * project_details["max_invocations"])
            else:
                avg_mints = np.mean(series[0:i, 1]) * project_details["max_invocations"]

            blocks_to_go = (project_details["max_invocations"] - project_details["invocations"]) / (avg_mints + 0.001)
            series[i, 2] = blocks_to_go

            if i > 20 and series[0, 0] == series[i, 0]:
                # This is no Dutch auction
                if np.sum(np.diff(series[i - 10:i,
                                  2]) < 0) > self.TIOLI_threshold and price_per_token_in_wei < self.price_threshold:
                    return 1

            if blocks_to_go < self.threshold and price_per_token_in_wei < self.price_threshold:
                return 1

            if i > 25 and blocks_to_go > self.cancel_threshold:
                return 0

            i += 1
