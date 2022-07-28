cp -r ../open-autonomy/packages/open_aea/protocols packages/open_aea
cp -r ../open-autonomy/packages/valory/agents/simple_abci packages/valory/agents
cp -r ../open-autonomy/packages/valory/agents/__init__.py packages/valory/agents
cp -r ../open-autonomy/packages/valory/connections/__init__.py packages/valory/connections
#manual> cp -r ../open-autonomy/packages/valory/connections/abci packages/valory/connections
cp -r ../open-autonomy/packages/valory/connections/http_client packages/valory/connections
cp -r ../open-autonomy/packages/valory/connections/ledger packages/valory/connections
cp -r ../open-autonomy/packages/valory/contracts/__init__.py packages/valory/contracts
cp -r ../open-autonomy/packages/valory/contracts/gnosis_safe packages/valory/contracts
cp -r ../open-autonomy/packages/valory/contracts/gnosis_safe_proxy_factory packages/valory/contracts
cp -r ../open-autonomy/packages/valory/contracts/multisend packages/valory/contracts
cp -r ../open-autonomy/packages/valory/protocols/__init__.py packages/valory/protocols
cp -r ../open-autonomy/packages/valory/protocols/abci packages/valory/protocols
cp -r ../open-autonomy/packages/valory/protocols/contract_api packages/valory/protocols
cp -r ../open-autonomy/packages/valory/protocols/http packages/valory/protocols
cp -r ../open-autonomy/packages/valory/protocols/ledger_api packages/valory/protocols
cp -r ../open-autonomy/packages/valory/skills/__init__.py packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/abstract_abci packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/abstract_round_abci packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/registration_abci packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/reset_pause_abci packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/safe_deployment_abci packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/simple_abci packages/valory/skills
cp -r ../open-autonomy/packages/valory/skills/transaction_settlement_abci packages/valory/skills
cp -r ../open-autonomy/scripts/__init__.py scripts/
cp -r ../open-autonomy/scripts/check_copyright.py scripts/
cp -r ../open-autonomy/scripts/check_packages.py scripts/
#manual > cp -r ../open-autonomy/tests/helpers/docker tests/helpers
cp -r ../open-autonomy/tests/helpers/__init__.py tests/helpers
cp -r ../open-autonomy/tests/helpers/async_utils.py tests/helpers
cp -r ../open-autonomy/tests/helpers/base.py tests/helpers
cp -r ../open-autonomy/tests/helpers/contracts.py tests/helpers
cp -r ../open-autonomy/tests/helpers/tendermint_utils.py tests/helpers
cp -r ../open-autonomy/tests/test_agents/__init__.py tests/test_agents
#manual > cp -r ../open-autonomy/tests/test_agents/base.py tests/test_agents
#manual > cp -r ../open-autonomy/tests/test_agents/test_simple_abci.py tests/test_agents
cp -r ../open-autonomy/tests/test_contracts/test_gnosis_safe tests/test_contracts
cp -r ../open-autonomy/tests/test_contracts/test_gnosis_safe_proxy_factory tests/test_contracts
#manual > cp -r ../open-autonomy/tests/test_contracts/base.py tests/test_contracts
cp -r ../open-autonomy/tests/test_skills/__init__.py tests/test_skills
cp -r ../open-autonomy/tests/test_skills/test_simple_abci tests/test_skills
echo "Manually sync: packages/valory/connections/abci, tests/helpers/docker, tests/test_agents/base.py, test_agents/test_simple_abci.py, tests/test_contracts/base.py"