from typing import Optional

import numpy as np
from aea.crypto.base import LedgerApi


# API Call format unclear at this point --> Variables naively assumed
class DecisionModel:
    def __init__(self):
        self.score = 0
        self.max_score = 5
        self.project_id: Optional[int] = None
        self.project_valid = 0
        self.threshold = 25
        self.price_threshold = 500000000000000000
        self.cancel_threshold = 10000
        self.TIOLI_threshold = 7
        self.project_done = False
        self.tokens_of_owner: Optional[list] = None
        self.royalties_of_project: Optional[dict] = None

    def static(self, project_details):
        if not project_details[-1] == '0x0000000000000000000000000000000000000000':
            self.score += 1
        if not project_details[2] == '':
            self.score += 1
        if self.score >= 1:
            self.project_valid = 1
        return self.project_valid

    def dynamic(self, project_details):
        # DYNAMIC PHASE
        # format discrimination
        i = 0
        series = np.array([])
        blocks_to_go = 10000000
        while self.project_valid == 1 and not self.project_done:
            price_per_token_in_wei = project_details[1]
            progress = project_details[-2] / project_details[-3]
            series = np.append(series, (price_per_token_in_wei, progress, blocks_to_go)).reshape(-1, 3)

            if i > 10:
                avg_mints = np.mean(series[i - 10:i, 1] * project_details[-3])
            else:
                avg_mints = np.mean(series[0:i, 1]) * project_details[-3]

            blocks_to_go = (project_details[-3] - project_details[-2]) / (avg_mints + 0.001)
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
