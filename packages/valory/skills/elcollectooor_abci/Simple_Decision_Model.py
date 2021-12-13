import numpy as np
import binascii
import datetime
from typing import Any, Callable, Dict, Optional, cast
from aea.crypto.base import LedgerApi


#### API Call format unclear at this point --> Variables naively assumed
class Decision_Model():
    def __init__(self):
        score = 0
        maxscore = 5
        project_id: Optional[int] = None
        project_valid = 0
        threshold = 25
        price_threshold = 500000000000000000
        cancel_threshold = 10000
        TIOLI_threshold = 7
        project_done = False

        tokens_of_owner: Optional[list] = None
        royalties_of_project: Optional[dict] = None

        # Static, intial phase

    def static(self,project_details):
        if not project_details[-1] == '0x0000000000000000000000000000000000000000':
            score += 1
#        if curation_status == True:
#            score +=1
        if not project_details[2] == '':
            score +=1
        #if max_invocations > 2:
        #    score +=1
#        if score/maxscore >= 0.6:
        if score >= 1:
            project_valid = 1
        return project_valid

    def dynamic(self,project_details,ledger_api : LedgerApi,contract_address :str):
#### DYNAMIC PHASE
#### Is there a way to see if there is a dutch auction or not?
#format discrimination
        import packages.collectooor.contracts.artblocks.contract.ArtBlocksContract as cls
        instance = cls.get_instance(ledger_api, contract_address)
        i=0
        Dutch = True
        series = np.array([])
        blocks_to_go = 10000000
        while project_valid == 1 and project_done == False:
            PricePerTokenInWei = project_details[1]
            Progress = project_details[-2]/project_details[-3]
            #if PricePerTokenInWei < Price_threshold:
            series = np.append(series,(PricePerTokenInWei, Progress, blocks_to_go)).reshape(-1,3)
            ##### Up to this point, we will have to call the core contract for projectIdToPricePerTokenInWei, projectDetails, tokensOfOwner, projectTokenInfo
            if i > 10:
                avg_mints = np.mean(series[i-10:i,1]*project_details[-3])
            else:
                avg_mints = np.mean(series[0:i,1])*project_details[-3]
            blocks_to_go = (project_details[-3] - project_details[-2]) / (avg_mints +0.001)
            series[i,2] = blocks_to_go

            if i > 20 and series[0,0] == series[i,0]:
                # This is no Dutch Auction
                if np.sum(np.diff(series[i-10:i,2]) < 0) > TIOLI_threshold and PricePerTokenInWei < price_threshold:
                    return 1

            if blocks_to_go < threshold and PricePerTokenInWei < price_threshold:
                return 1

            if i > 25 and blocks_to_go > cancel_threshold:
                return 0
            i += 1




