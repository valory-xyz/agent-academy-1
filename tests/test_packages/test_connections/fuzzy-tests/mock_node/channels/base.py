from packages.valory.connections.abci.tendermint.abci import (
    types_pb2 as abci_types,
)


class BaseChannel:

    def __init__(self, **kwargs):
        pass

    def send_info(
            self,
            request: abci_types.RequestInfo
    ) -> abci_types.ResponseInfo:
        raise NotImplemented

    def send_echo(
            self,
            request: abci_types.RequestEcho
    ) -> abci_types.ResponseEcho:
        raise NotImplemented

    def send_flush(
            self,
            request: abci_types.RequestFlush
    ) -> abci_types.ResponseFlush:
        raise NotImplemented

    def send_set_option(
            self,
            request: abci_types.RequestSetOption
    ) -> abci_types.ResponseSetOption:
        raise NotImplemented

    def send_deliver_tx(
            self,
            request: abci_types.RequestDeliverTx
    ) -> abci_types.ResponseDeliverTx:
        raise NotImplemented

    def send_check_tx(
            self,
            request: abci_types.RequestCheckTx
    ) -> abci_types.ResponseCheckTx:
        raise NotImplemented

    def send_query(
            self,
            request: abci_types.RequestQuery
    ) -> abci_types.ResponseQuery:
        raise NotImplemented

    def send_commit(
            self,
            request: abci_types.RequestCommit
    ) -> abci_types.ResponseCommit:
        raise NotImplemented

    def send_init_chain(
            self,
            request: abci_types.RequestInitChain
    ) -> abci_types.ResponseInitChain:
        raise NotImplemented

    def send_begin_block(
            self,
            request: abci_types.RequestBeginBlock
    ) -> abci_types.ResponseBeginBlock:
        raise NotImplemented

    def send_end_block(self, request: abci_types.RequestEndBlock) -> abci_types.ResponseEndBlock:
        raise NotImplemented

    def send_list_snapshots(
            self,
            request: abci_types.RequestListSnapshots
    ) -> abci_types.ResponseListSnapshots:
        raise NotImplemented

    def send_offer_snapshot(
            self,
            request: abci_types.RequestOfferSnapshot
    ) -> abci_types.ResponseOfferSnapshot:
        raise NotImplemented

    def send_load_snapshot_chunk(
            self,
            request: abci_types.RequestLoadSnapshotChunk
    ) -> abci_types.ResponseLoadSnapshotChunk:
        raise NotImplemented

    def send_apply_snapshot_chunk(
            self, request: abci_types.RequestApplySnapshotChunk
    ) -> abci_types.ResponseApplySnapshotChunk:
        raise NotImplemented
