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
"""Connection to interact with an ABCI server."""
import asyncio
import logging
import signal
import subprocess  # nosec
from asyncio import AbstractEventLoop, AbstractServer, CancelledError, Task
from io import BytesIO
from logging import Logger
from typing import Any, Dict, List, Optional, Tuple, Type, cast

import grpc
from aea.configurations.base import PublicId
from aea.connections.base import Connection, ConnectionStates
from aea.mail.base import Envelope
from aea.protocols.dialogue.base import DialogueLabel

from packages.valory.connections.abci import PUBLIC_ID as CONNECTION_PUBLIC_ID
from packages.valory.connections.abci.dialogues import AbciDialogues
from packages.valory.connections.abci.tendermint.abci import (
    types_pb2 as tendermint_dot_abci_dot_types__pb2,
)
from packages.valory.connections.abci.tendermint.abci import types_pb2_grpc
from packages.valory.connections.abci.tendermint.abci.types_pb2 import (  # type: ignore
    Request,
    Response,
)
from packages.valory.connections.abci.tendermint_decoder import (
    _TendermintProtocolDecoder,
)
from packages.valory.connections.abci.tendermint_encoder import (
    _TendermintProtocolEncoder,
)
from packages.valory.protocols.abci import AbciMessage


PUBLIC_ID = CONNECTION_PUBLIC_ID

DEFAULT_LISTEN_ADDRESS = "0.0.0.0"  # nosec
DEFAULT_ABCI_PORT = 26658
MAX_READ_IN_BYTES = 64 * 1024  # Max we'll consume on a read stream


class _TendermintABCISerializer:
    """(stateless) utility class to encode/decode messages for the communication with Tendermint."""

    @classmethod
    def encode_varint(cls, number: int) -> bytes:
        """Encode a number in varint coding."""
        # Shift to int64
        number = number << 1
        buf = b""
        while True:
            towrite = number & 0x7F
            number >>= 7
            if number:
                buf += bytes((towrite | 0x80,))
            else:
                buf += bytes((towrite,))
                break
        return buf

    @classmethod
    def decode_varint(cls, buffer: BytesIO) -> int:
        """Decode a number from its varint coding."""
        shift = 0
        result = 0
        while True:
            i = cls._read_one(buffer)
            result |= (i & 0x7F) << shift
            shift += 7
            if not i & 0x80:
                break
        return result

    @classmethod
    def _read_one(cls, buffer: BytesIO) -> int:
        """Read one byte to decode a varint."""
        character = buffer.read(1)
        if character == b"":
            raise EOFError("Unexpected EOF while reading bytes")
        return ord(character)

    @classmethod
    def write_message(cls, message: Response) -> bytes:
        """Write a message in a buffer."""
        buffer = BytesIO(b"")
        protobuf_bytes = message.SerializeToString()
        encoded = cls.encode_varint(len(protobuf_bytes))
        buffer.write(encoded)
        buffer.write(protobuf_bytes)
        return buffer.getvalue()

    @classmethod
    def read_messages(cls, buffer: BytesIO, message_cls: Type) -> Request:
        """Return an iterator over the messages found in the `reader` buffer."""
        while True:
            try:
                length = cls.decode_varint(buffer) >> 1
            except EOFError:
                return
            data = buffer.read(length)
            if len(data) < length:
                return  # pragma: nocover
            message = message_cls()
            message.ParseFromString(data)

            yield message


class ABCIApplicationServicer(types_pb2_grpc.ABCIApplicationServicer):
    def __init__(
        self, request_queue: asyncio.Queue, dialogues: AbciDialogues, target_skill: str
    ):
        """
        Initializes the abci handler.

        :param request_queue: queue holding translated abci messages.
        :param dialogues: dialogues
        :param target_skill: target skill of messages
        """
        super().__init__()
        self._request_queue = request_queue
        self._dialogues = dialogues
        self._target_skill = target_skill
        self._response_queues = {
            AbciMessage.Performative.RESPONSE_FLUSH: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_INFO: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_DELIVER_TX: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_CHECK_TX: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_QUERY: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_COMMIT: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_INIT_CHAIN: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_BEGIN_BLOCK: asyncio.Queue(),
            AbciMessage.Performative.RESPONSE_END_BLOCK: asyncio.Queue(),
        }

    async def send(self, envelope: Envelope):
        message = cast(AbciMessage, envelope.message)
        dialogue = self._dialogues.update(message)
        if dialogue is None:
            return

        await self._response_queues[message.performative].put(envelope)

    def Echo(self, request, context):
        context.set_code(grpc.StatusCode.OK)
        response = tendermint_dot_abci_dot_types__pb2.ResponseEcho()
        response.message = request.message

        return response

    async def Flush(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(flush=request)
        request, message = _TendermintProtocolDecoder.request_flush(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        _ = await self._response_queues[AbciMessage.Performative.RESPONSE_FLUSH].get()

        context.set_code(grpc.StatusCode.OK)
        response = tendermint_dot_abci_dot_types__pb2.ResponseFlush()

        return response

    async def Info(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(info=request)
        request, message = _TendermintProtocolDecoder.request_info(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_INFO
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_info(message)
        context.set_code(grpc.StatusCode.OK)

        return response.info

    async def DeliverTx(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(deliver_tx=request)
        request, message = _TendermintProtocolDecoder.request_deliver_tx(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_DELIVER_TX
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_deliver_tx(message)
        context.set_code(grpc.StatusCode.OK)

        return response.deliver_tx

    async def CheckTx(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(check_tx=request)
        request, message = _TendermintProtocolDecoder.request_check_tx(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_CHECK_TX
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_check_tx(message)
        context.set_code(grpc.StatusCode.OK)

        return response.check_tx

    async def Query(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(query=request)
        request, message = _TendermintProtocolDecoder.request_query(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_QUERY
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_query(message)
        context.set_code(grpc.StatusCode.OK)

        return response.query

    async def Commit(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(commit=request)
        request, message = _TendermintProtocolDecoder.request_commit(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_COMMIT
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_commit(message)
        context.set_code(grpc.StatusCode.OK)

        return response.commit

    async def InitChain(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(init_chain=request)
        request, message = _TendermintProtocolDecoder.request_init_chain(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_INIT_CHAIN
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_init_chain(message)
        context.set_code(grpc.StatusCode.OK)

        return response.init_chain

    async def BeginBlock(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(begin_block=request)
        request, message = _TendermintProtocolDecoder.request_begin_block(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_BEGIN_BLOCK
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_begin_block(message)
        context.set_code(grpc.StatusCode.OK)

        return response.begin_block

    async def EndBlock(self, request, context):
        request = tendermint_dot_abci_dot_types__pb2.Request(end_block=request)
        request, message = _TendermintProtocolDecoder.request_end_block(
            request, self._dialogues, self._target_skill
        )
        envelope = Envelope(to=request.to, sender=request.sender, message=request)

        await self._request_queue.put(envelope)
        message = cast(
            AbciMessage,
            (
                await self._response_queues[
                    AbciMessage.Performative.RESPONSE_END_BLOCK
                ].get()
            ).message,
        )

        response = _TendermintProtocolEncoder.response_end_block(message)
        context.set_code(grpc.StatusCode.OK)

        return response.end_block


class GrpcServerChannel:  # pylint: disable=too-many-instance-attributes
    """TCP server channel to handle incoming communication from the Tendermint node."""

    def __init__(
        self,
        target_skill_id: PublicId,
        address: str,
        port: int,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the TCP server.

        :param target_skill_id: the public id of the target skill.
        :param address: the listen address.
        :param port: the port to listen from.
        :param logger: the logger.
        """
        self.target_skill_id = target_skill_id
        self.address = address
        self.port = port
        self.logger = logger

        # channel state
        self._loop: Optional[AbstractEventLoop] = None
        self._dialogues = AbciDialogues()
        self._is_stopped: bool = True
        self.queue: Optional[asyncio.Queue] = None
        self._server: Optional[any] = None
        self._server_task: Optional[Task] = None
        self._servicer: Optional[ABCIApplicationServicer] = None

    @property
    def is_stopped(self) -> bool:
        """Check that the channel is stopped."""
        return self._is_stopped

    async def _start_server(self):
        self.logger.info("Starting gRPC server")
        server = grpc.aio.server()
        self._servicer = ABCIApplicationServicer(
            self.queue, self._dialogues, str(self.target_skill_id)
        )
        types_pb2_grpc.add_ABCIApplicationServicer_to_server(self._servicer, server)
        server.add_insecure_port(f"[::]:{self.port}")
        self._server = server
        await self._server.start()
        await self._server.wait_for_termination()

    async def connect(self, loop: AbstractEventLoop) -> None:
        """
        Connect.

        Upon TCP Channel connection, start the TCP Server asynchronously.

        :param loop: asyncio event loop
        """
        if not self._is_stopped:  # pragma: nocover
            return
        self._loop = loop
        self._is_stopped = False
        self.queue = asyncio.Queue()

        asyncio.create_task(self._start_server())

    async def disconnect(self) -> None:
        """Disconnect the channel"""
        if self.is_stopped:  # pragma: nocover
            return
        self._is_stopped = True
        await self._server.stop(0)

        self.queue = None
        self._server = None

    async def get_message(self) -> Envelope:
        """Get a message from the queue."""
        return await cast(asyncio.Queue, self.queue).get()

    async def send(self, envelope: Envelope) -> None:
        """Send a message."""
        await self._servicer.send(envelope)


class TcpServerChannel:  # pylint: disable=too-many-instance-attributes
    """TCP server channel to handle incoming communication from the Tendermint node."""

    def __init__(
        self,
        target_skill_id: PublicId,
        address: str,
        port: int,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the TCP server.

        :param target_skill_id: the public id of the target skill.
        :param address: the listen address.
        :param port: the port to listen from.
        :param logger: the logger.
        """
        self.target_skill_id = target_skill_id
        self.address = address
        self.port = port
        self.logger = logger

        # channel state
        self._loop: Optional[AbstractEventLoop] = None
        self._dialogues = AbciDialogues()
        self._is_stopped: bool = True
        self.queue: Optional[asyncio.Queue] = None
        self._server: Optional[AbstractServer] = None
        self._server_task: Optional[Task] = None
        # a single Tendermint opens four concurrent connections:
        # https://docs.tendermint.com/master/spec/abci/apps.html
        # this dictionary keeps track of the reader-writer stream pair
        # by socket name (ip address and port)
        self._streams_by_socket: Dict[
            str, Tuple[asyncio.StreamReader, asyncio.StreamWriter]
        ] = {}
        # this dictionary associates requests to socket name
        # such that responses are sent to the right receiver
        self._request_id_to_socket: Dict[DialogueLabel, str] = {}

    @property
    def is_stopped(self) -> bool:
        """Check that the channel is stopped."""
        return self._is_stopped

    async def connect(self, loop: AbstractEventLoop) -> None:
        """
        Connect.

        Upon TCP Channel connection, start the TCP Server asynchronously.

        :param loop: asyncio event loop
        """
        if not self._is_stopped:  # pragma: nocover
            return
        self._loop = loop
        self._is_stopped = False
        self.queue = asyncio.Queue()

        self._server = await asyncio.start_server(
            self.receive_messages, host=self.address, port=self.port, loop=self._loop
        )

    async def disconnect(self) -> None:
        """Disconnect the channel"""
        if self.is_stopped:  # pragma: nocover
            return
        self._is_stopped = True
        self._server = cast(AbstractServer, self._server)
        self._server.close()
        await self._server.wait_closed()

        self.queue = None
        self._server = None
        self._streams_by_socket = {}
        self._request_id_to_socket = {}

    async def receive_messages(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Receive incoming messages."""
        self.logger = cast(Logger, self.logger)
        self.queue = cast(asyncio.Queue, self.queue)
        ip_address, socket, *_ = writer.get_extra_info("peername")
        peer_name = f"{ip_address}:{socket}"
        self._streams_by_socket[peer_name] = (reader, writer)
        self.logger.debug(f"Connection with Tendermint @ {peer_name}")

        while not self.is_stopped:
            data = BytesIO()

            try:
                bits = await reader.read(MAX_READ_IN_BYTES)
            except CancelledError:  # pragma: nocover
                self.logger.debug(f"Read task for peer {peer_name} cancelled.")
                return
            if len(bits) == 0:
                self.logger.error(f"Tendermint node {peer_name} closed connection.")
                # break to the _stop if the connection stops
                break

            self.logger.debug(f"Received {len(bits)} bytes from connection {peer_name}")
            data.write(bits)
            data.seek(0)

            # Tendermint prefixes each serialized protobuf message
            # with varint encoded length. We use the 'data' buffer to
            # keep track of where we are in the byte stream and progress
            # based on the length encoding
            for message in _TendermintABCISerializer.read_messages(data, Request):
                if self.is_stopped:
                    break
                req_type = message.WhichOneof("value")
                self.logger.debug(f"Received message of type: {req_type}")
                request, dialogue = _TendermintProtocolDecoder.process(
                    message, self._dialogues, str(self.target_skill_id)
                )
                # associate request to peer, so we remember who to reply to
                self._request_id_to_socket[
                    dialogue.incomplete_dialogue_label
                ] = peer_name
                if request is not None:
                    envelope = Envelope(
                        to=request.to, sender=request.sender, message=request
                    )
                    await self.queue.put(envelope)
                else:  # pragma: nocover
                    self.logger.warning(f"Decoded request {req_type} was None.")

    async def get_message(self) -> Envelope:
        """Get a message from the queue."""
        return await cast(asyncio.Queue, self.queue).get()

    async def send(self, envelope: Envelope) -> None:
        """Send a message."""
        self.logger = cast(Logger, self.logger)
        message = cast(AbciMessage, envelope.message)
        dialogue = self._dialogues.update(message)
        if dialogue is None:  # pragma: nocover
            self.logger.warning(f"Could not create dialogue for message={message}")
            return

        peer_name = self._request_id_to_socket[dialogue.incomplete_dialogue_label]
        _reader, writer = self._streams_by_socket[peer_name]
        protobuf_message = _TendermintProtocolEncoder.process(message)
        data = _TendermintABCISerializer.write_message(protobuf_message)
        self.logger.debug(f"Writing {len(data)} bytes")
        writer.write(data)


class TendermintParams:  # pylint: disable=too-few-public-methods
    """Tendermint node parameters."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        proxy_app: str,
        rpc_laddr: str,
        p2p_laddr: str,
        p2p_seeds: List[str],
        consensus_create_empty_blocks: bool,
        home: Optional[str] = None,
        use_grpc: bool = False,
    ):
        """
        Initialize the parameters to the Tendermint node.

        :param proxy_app: ABCI address.
        :param rpc_laddr: RPC address.
        :param p2p_laddr: P2P address.
        :param p2p_seeds: P2P seeds.
        :param use_grpc: Wheter to use a gRPC server, or TSP
        :param consensus_create_empty_blocks: if true, Tendermint node creates empty blocks.
        :param home: Tendermint's home directory.
        """
        self.proxy_app = proxy_app
        self.rpc_laddr = rpc_laddr
        self.p2p_laddr = p2p_laddr
        self.p2p_seeds = p2p_seeds
        self.consensus_create_empty_blocks = consensus_create_empty_blocks
        self.home = home
        self.use_grpc = use_grpc


class TendermintNode:
    """A class to manage a Tendermint node."""

    def __init__(self, params: TendermintParams, logger: Optional[Logger] = None):
        """
        Initialize a Tendermint node.

        :param params: the parameters.
        :param logger: the logger.
        """
        self.params = params
        self.logger = logger or logging.getLogger()

        self._process: Optional[subprocess.Popen] = None

    def _build_init_command(self) -> List[str]:
        """Build the 'init' command."""
        cmd = [
            "tendermint",
            "init",
        ]
        if self.params.home is not None:  # pragma: nocover
            cmd += ["--home", self.params.home]
        return cmd

    def _build_node_command(self) -> List[str]:
        """Build the 'node' command."""
        cmd = [
            "tendermint",
            "node",
            f"--proxy_app={self.params.proxy_app}",
            f"--rpc.laddr={self.params.rpc_laddr}",
            f"--p2p.laddr={self.params.p2p_laddr}",
            f"--p2p.seeds={','.join(self.params.p2p_seeds)}",
            f"--consensus.create_empty_blocks={str(self.params.consensus_create_empty_blocks).lower()}",
        ]

        if self.params.use_grpc:
            cmd += ["--abci=grpc"]

        if self.params.home is not None:  # pragma: nocover
            cmd += ["--home", self.params.home]
        return cmd

    def init(self) -> None:
        """Initialize Tendermint node."""
        cmd = self._build_init_command()
        subprocess.call(cmd)  # nosec

    def start(self) -> None:
        """Start a Tendermint node process."""
        if self._process is not None:  # pragma: nocover
            return
        cmd = self._build_node_command()
        self._process = subprocess.Popen(  # nosec # pylint: disable=consider-using-with
            cmd
        )

    def stop(self) -> None:
        """Stop a Tendermint node process."""
        if self._process is None:  # pragma: nocover
            return
        self._process.send_signal(signal.SIGTERM)
        self._process.wait(timeout=30)
        poll = self._process.poll()
        if poll is None:  # pragma: nocover
            self._process.terminate()
            self._process.wait(2)
        self._process = None


class ABCIServerConnection(Connection):  # pylint: disable=too-many-instance-attributes
    """ABCI server."""

    connection_id = PUBLIC_ID
    params: Optional[TendermintParams] = None
    node: Optional[TendermintNode] = None

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the connection.

        :param kwargs: keyword arguments passed to component base
        """
        super().__init__(**kwargs)  # pragma: no cover

        self._process_connection_params()
        self._process_tendermint_params()

        if self.use_grpc:
            self.channel = GrpcServerChannel(
                self.target_skill_id, address=self.host, port=self.port
            )
        else:
            self.channel = TcpServerChannel(
                self.target_skill_id, address=self.host, port=self.port
            )

    def _process_connection_params(self) -> None:
        """
        Process the connection parameters.

        The parameters to process are:
        - host
        - port
        - target_skill_id
        """
        self.host = cast(str, self.configuration.config.get("host"))
        self.port = cast(int, self.configuration.config.get("port"))
        target_skill_id_string = cast(
            Optional[str], self.configuration.config.get("target_skill_id")
        )

        if (
            self.host is None or self.port is None or target_skill_id_string is None
        ):  # pragma: no cover
            raise ValueError("host and port and target_skill_id must be set!")
        target_skill_id = PublicId.try_from_str(target_skill_id_string)
        if target_skill_id is None:  # pragma: no cover
            raise ValueError("Provided target_skill_id is not a valid public id.")
        self.target_skill_id = target_skill_id

    def _process_tendermint_params(self) -> None:
        """
        Process the Tendermint parameters.

        In particular, if use_tendermint is False, do nothing.
        Else, process the following parameters:
        - rpc_laddr: the listening address for RPC communication
        - p2p_laddr: the listening address for P2P communication
        - p2p_seeds: a comma-separated list of IP addresses and ports
        """
        self.use_tendermint = cast(
            bool, self.configuration.config.get("use_tendermint")
        )
        self.use_grpc = cast(bool, self.configuration.config.get("use_grpc"))

        if not self.use_tendermint:
            return
        tendermint_config = self.configuration.config.get("tendermint_config", {})
        rpc_laddr = cast(str, tendermint_config.get("rpc_laddr"))
        p2p_laddr = cast(str, tendermint_config.get("p2p_laddr"))
        p2p_seeds = cast(List[str], tendermint_config.get("p2p_seeds"))
        home = cast(str, tendermint_config.get("home"))
        consensus_create_empty_blocks = cast(
            bool, tendermint_config.get("consensus_create_empty_blocks")
        )
        proxy_app = f"tcp://{self.host}:{self.port}"
        self.params = TendermintParams(
            proxy_app,
            rpc_laddr,
            p2p_laddr,
            p2p_seeds,
            consensus_create_empty_blocks,
            home,
            self.use_grpc,
        )
        self.node = TendermintNode(self.params, self.logger)

    async def connect(self) -> None:
        """
        Set up the connection.

        In the implementation, remember to update 'connection_status' accordingly.
        """
        if self.is_connected:  # pragma: no cover
            return

        self.state = ConnectionStates.connecting
        if self.use_tendermint:
            self.node = cast(TendermintNode, self.node)
            self.node.init()
            self.node.start()
        self.channel.logger = self.logger
        await self.channel.connect(loop=self.loop)
        if self.channel.is_stopped:  # pragma: no cover
            self.state = ConnectionStates.disconnected
            return
        self.state = ConnectionStates.connected

    async def disconnect(self) -> None:
        """
        Tear down the connection.

        In the implementation, remember to update 'connection_status' accordingly.
        """
        if self.is_disconnected:  # pragma: no cover
            return

        self.state = ConnectionStates.disconnecting
        await self.channel.disconnect()
        if self.use_tendermint:
            self.node = cast(TendermintNode, self.node)
            self.node.stop()
        self.state = ConnectionStates.disconnected

    async def send(self, envelope: Envelope) -> None:
        """
        Send an envelope.

        :param envelope: the envelope to send.
        """
        self._ensure_connected()
        await self.channel.send(envelope)

    async def receive(self, *args: Any, **kwargs: Any) -> Optional[Envelope]:
        """
        Receive an envelope. Blocking.

        :param args: arguments to receive
        :param kwargs: keyword arguments to receive
        :return: the envelope received, if present.  # noqa: DAR202
        """
        self._ensure_connected()
        try:
            return await self.channel.get_message()
        except CancelledError:  # pragma: no cover
            return None
