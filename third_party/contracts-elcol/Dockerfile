FROM node:16.7.0 as builder

RUN mkdir elcol
COPY . ./elcol
WORKDIR ./elcol

RUN yarn install

ENTRYPOINT ["yarn", "run", "hardhat", "extra-compile", "--port", "8545"]

# TODO: introduce second stage (runner)
