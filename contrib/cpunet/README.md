Contents
========

This directory contains tools related to CPUNet, both for running a CPUNet
yourself and for using one.

Status
======

Currently this is a Work In Progress. It can run CPUNet and mine blocks. Any
peer nodes must be added manually. See TODO below.

Getting Started
===============

This fork of bitcoin cannot run mainnet, testnet, or signet. All commands must
have `-cpunet` or they will fail.

1. Compile CPUNet:

        ./configure make -j16

2. Run cpunet node:

        src/bitcoind -cpunet -zmqpubsequence=tcp://127.0.0.1:28338

    or

        # if you have already created the wallet
        src/bitcoind -cpunet -wallet=cpunet -zmqpubsequence=tcp://127.0.0.1:28338

3. Create and open a wallet: (only needs to be done once)

        src/bitcoin-cli -cpunet createwallet cpunet
        src/bitcoin-cli -cpunet loadwallet cpunet

4. Generate blocks:

        contrib/cpunet/miner --cli=src/bitcoin-cli --ongoing --address `src/bitcoin-cli -cpunet getnewaddress` --grind-cmd="src/bitcoin-util -cpunet -ntasks=1 grind"

TODO
====

1. Set up a seed node so we can find peers

2. Create a docker container to run this

3. Add an argument -my-block-latency artificial latency parameter that will
   delay starting mining a new block when the block found is mine.

4. Add an argument -other-block-latency artificial latency parameter that will
   delay starting mining a new block when a new block is found by another miner
   and announced to contrib/cpunet/miner via ZMQ. (Related to "Clean Jobs"
   stratum parameter)

5. Add SV2 support and use an external SV2 miner instead of bitcoin-utils

6. Add a -share-difficulty argument to mine shares of lower difficulty than the
   block target

7. Add a -share-cmd to submit shares to a pool.

8. The way I changed the PoW hash means that it screws up mainnet, signet, and
   the testnets and assertions have to be commented out. Therefore this cannot
   be merged into Bitcoin unless we find a way to detect `-cpunet` and calculate
   the block hash differently. I don't see a way to get the network parameters
   into CBlockHeader to make this conditional. Looking for a good idea here.

Other options
-------------

The --debug and --quiet options are available to control how noisy the signet miner's output is.

Instead of specifying --ongoing, you can specify --max-blocks=N to mine N blocks and stop.

You can add the -ntasks=<n> parameter to `bitcoin-util grid` to make it use
fewer than the number of cores on your machine. By default it will use all cores
available.

Instead of using a single address, a ranged descriptor may be provided via the --descriptor parameter, with the reward for the block at height H being sent to the H'th address generated from the descriptor.

