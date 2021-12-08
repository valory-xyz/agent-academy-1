from collections import Generator

from packages.valory.skills.elcollectooor_abci.behaviours import ElCollectooorABCIBaseState, benchmark_tool
from packages.valory.skills.elcollectooor_abci.payloads import DecisionPayload
from packages.valory.skills.elcollectooor_abci.rounds import DecisionRound


class DecisionRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "decision"
    matching_round = DecisionRound

    def async_act(self) -> Generator:
        # TODO: define retry mechanism

        with benchmark_tool.measure(
                self,
        ).local():
            # fetch an active project
            decision = await self._make_decision(self.period_state.most_voted_project)
            payload = DecisionPayload(
                self.context.agent_address,
                decision,
            )

            with benchmark_tool.measure(
                    self,
            ).consensus():
                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

    async def _make_decision(self, project_details: dict) -> int:
        """ Method to that decides on an outcome """
        self.context.logger.info(f'making decision on project with id {project_details["project_id"]}')
        decision = 1  # TODO: add decision algorithm
        self.context.logger.info(f'decided {decision} for project with id {project_details["project_id"]}')

        return decision
