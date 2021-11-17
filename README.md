# agent-academy-1
Valory's Agent Academy 1 - participant repo

## Requirements

- `Python >= 3.7`
- [Tendermint](https://docs.tendermint.com/master/introduction/install.html)
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `>=v0.6.0`

## Simple ABCI example

Create a virtual environment with all development dependencies: 

```bash
make new_env
```

Enter virtual environment:

``` bash
pipenv shell
```

To run the test:

``` bash
pytest tests/test_simple_abci.py::TestABCIPriceEstimationSingleAgent
```

or

``` bash
pytest tests/test_simple_abci.py::TestABCIPriceEstimationTwoAgents
```

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make lint`, `make static` and `make pylint`, as well as `make hashes`.
