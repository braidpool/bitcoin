#!/usr/bin/env python3
# Copyright (c) 2014-2022 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test RPCs that retrieve information from the mempool."""

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    assert_raises_rpc_error,
)
from test_framework.wallet import MiniWallet


class RPCMempoolInfoTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 1

    def test_removetxfrommempool(self):
        """Test for removetxfrommempool RPC functionality"""
        self.log.info("Starting removetxfrommempool tests")
        node = self.nodes[0]
        initial_mempool_size = len(node.getrawmempool())

        # Basic transaction removal
        tx1 = self.wallet.send_self_transfer(from_node=node)
        txid1 = tx1["txid"]
        assert txid1 in node.getrawmempool()
        assert_equal(len(node.getrawmempool()), initial_mempool_size + 1)
        result = node.removetxfrommempool(txid1)
        assert_equal(result["removed"], True)

        # Verify transaction is no longer in mempool
        assert txid1 not in node.getrawmempool()
        assert_equal(len(node.getrawmempool()), initial_mempool_size)

        # Removing non-existent transaction
        fake_txid = "0" * 64
        result = node.removetxfrommempool(fake_txid)
        assert_equal(result["removed"], False)

        # Recursive removal (parent-child transactions)
        # Create parent transaction
        parent_tx = self.wallet.send_self_transfer(from_node=node)
        parent_txid = parent_tx["txid"]

        # Create child transaction spending from parent
        child_tx = self.wallet.send_self_transfer(
            from_node=node,
            utxo_to_spend=parent_tx["new_utxo"]
        )
        child_txid = child_tx["txid"]
        mempool = node.getrawmempool()
        assert parent_txid in mempool
        assert child_txid in mempool
        assert_equal(len(mempool), initial_mempool_size + 2)

        # Remove parent transaction
        result = node.removetxfrommempool(parent_txid)
        assert_equal(result["removed"], True)

        # Verify both parent and child are removed
        mempool = node.getrawmempool()
        assert parent_txid not in mempool
        assert child_txid not in mempool
        assert_equal(len(mempool), initial_mempool_size)

        # Transaction chain removal
        # Create a chain of 3 transactions: tx1 -> tx2 -> tx3
        chain_tx1 = self.wallet.send_self_transfer(from_node=node)
        chain_tx2 = self.wallet.send_self_transfer(
            from_node=node,
            utxo_to_spend=chain_tx1["new_utxo"]
        )
        chain_tx3 = self.wallet.send_self_transfer(
            from_node=node,
            utxo_to_spend=chain_tx2["new_utxo"]
        )

        # Verify all transactions are in mempool
        mempool = node.getrawmempool()
        assert_equal(len(mempool), initial_mempool_size + 3)
        for tx in [chain_tx1, chain_tx2, chain_tx3]:
            assert tx["txid"] in mempool

        # Remove the middle transaction (chain_tx2)
        result = node.removetxfrommempool(chain_tx2["txid"])
        assert_equal(result["removed"], True)

        # chain_tx2 and chain_tx3 should be removed, chain_tx1 should remain
        mempool = node.getrawmempool()
        assert chain_tx1["txid"] in mempool
        assert chain_tx2["txid"] not in mempool
        assert chain_tx3["txid"] not in mempool
        assert_equal(len(mempool), initial_mempool_size + 1)

        # Test with invalid txid format
        assert_raises_rpc_error(-8, "txid must be of length 64", node.removetxfrommempool, "invalid")

        # Test with wrong length hex (too short)
        assert_raises_rpc_error(-8, "txid must be of length 64", node.removetxfrommempool, "a" * 63)

        # Test with wrong length hex (too long)
        assert_raises_rpc_error(-8, "txid must be of length 64", node.removetxfrommempool, "a" * 65)

        # Test with no parameters
        assert_raises_rpc_error(-1, "", node.removetxfrommempool)

        # Test with valid hex but non-existent txid
        valid_but_fake_txid = "a" * 64
        result = node.removetxfrommempool(valid_but_fake_txid)
        assert_equal(result["removed"], False)

        # Test removing the same transaction twice
        double_remove_tx = self.wallet.send_self_transfer(from_node=node)
        double_remove_txid = double_remove_tx["txid"]
        result1 = node.removetxfrommempool(double_remove_txid)
        assert_equal(result1["removed"], True)
        result2 = node.removetxfrommempool(double_remove_txid)
        assert_equal(result2["removed"], False)

        # Clean up remaining transactions
        node.removetxfrommempool(chain_tx1["txid"])

        # Verify mempool is clean
        assert_equal(len(node.getrawmempool()), initial_mempool_size)

        self.log.info("All removetxfrommempool tests completed successfully")

    def run_test(self):
        self.wallet = MiniWallet(self.nodes[0])
        confirmed_utxo = self.wallet.get_utxo()

        # Create a tree of unconfirmed transactions in the mempool:
        #             txA
        #             / \
        #            /   \
        #           /     \
        #          /       \
        #         /         \
        #       txB         txC
        #       / \         / \
        #      /   \       /   \
        #    txD   txE   txF   txG
        #            \   /
        #             \ /
        #             txH

        def create_tx(**kwargs):
            return self.wallet.send_self_transfer_multi(
                from_node=self.nodes[0],
                **kwargs,
            )

        txA = create_tx(utxos_to_spend=[confirmed_utxo], num_outputs=2)
        txB = create_tx(utxos_to_spend=[txA["new_utxos"][0]], num_outputs=2)
        txC = create_tx(utxos_to_spend=[txA["new_utxos"][1]], num_outputs=2)
        txD = create_tx(utxos_to_spend=[txB["new_utxos"][0]], num_outputs=1)
        txE = create_tx(utxos_to_spend=[txB["new_utxos"][1]], num_outputs=1)
        txF = create_tx(utxos_to_spend=[txC["new_utxos"][0]], num_outputs=2)
        txG = create_tx(utxos_to_spend=[txC["new_utxos"][1]], num_outputs=1)
        txH = create_tx(utxos_to_spend=[txE["new_utxos"][0],txF["new_utxos"][0]], num_outputs=1)
        txidA, txidB, txidC, txidD, txidE, txidF, txidG, txidH = [
            tx["txid"] for tx in [txA, txB, txC, txD, txE, txF, txG, txH]
        ]

        mempool = self.nodes[0].getrawmempool()
        assert_equal(len(mempool), 8)
        for txid in [txidA, txidB, txidC, txidD, txidE, txidF, txidG, txidH]:
            assert_equal(txid in mempool, True)

        self.log.info("Find transactions spending outputs")
        result = self.nodes[0].gettxspendingprevout([ {'txid' : confirmed_utxo['txid'], 'vout' : 0}, {'txid' : txidA, 'vout' : 1} ])
        assert_equal(result, [ {'txid' : confirmed_utxo['txid'], 'vout' : 0, 'spendingtxid' : txidA}, {'txid' : txidA, 'vout' : 1, 'spendingtxid' : txidC} ])

        self.log.info("Find transaction spending multiple outputs")
        result = self.nodes[0].gettxspendingprevout([ {'txid' : txidE, 'vout' : 0}, {'txid' : txidF, 'vout' : 0} ])
        assert_equal(result, [ {'txid' : txidE, 'vout' : 0, 'spendingtxid' : txidH}, {'txid' : txidF, 'vout' : 0, 'spendingtxid' : txidH} ])

        self.log.info("Find no transaction when output is unspent")
        result = self.nodes[0].gettxspendingprevout([ {'txid' : txidH, 'vout' : 0} ])
        assert_equal(result, [ {'txid' : txidH, 'vout' : 0} ])
        result = self.nodes[0].gettxspendingprevout([ {'txid' : txidA, 'vout' : 5} ])
        assert_equal(result, [ {'txid' : txidA, 'vout' : 5} ])

        self.log.info("Mixed spent and unspent outputs")
        result = self.nodes[0].gettxspendingprevout([ {'txid' : txidB, 'vout' : 0}, {'txid' : txidG, 'vout' : 3} ])
        assert_equal(result, [ {'txid' : txidB, 'vout' : 0, 'spendingtxid' : txidD}, {'txid' : txidG, 'vout' : 3} ])

        self.log.info("Unknown input fields")
        assert_raises_rpc_error(-3, "Unexpected key unknown", self.nodes[0].gettxspendingprevout, [{'txid' : txidC, 'vout' : 1, 'unknown' : 42}])

        self.log.info("Invalid vout provided")
        assert_raises_rpc_error(-8, "Invalid parameter, vout cannot be negative", self.nodes[0].gettxspendingprevout, [{'txid' : txidA, 'vout' : -1}])

        self.log.info("Invalid txid provided")
        assert_raises_rpc_error(-3, "JSON value of type number for field txid is not of expected type string", self.nodes[0].gettxspendingprevout, [{'txid' : 42, 'vout' : 0}])

        self.log.info("Missing outputs")
        assert_raises_rpc_error(-8, "Invalid parameter, outputs are missing", self.nodes[0].gettxspendingprevout, [])

        self.log.info("Missing vout")
        assert_raises_rpc_error(-3, "Missing vout", self.nodes[0].gettxspendingprevout, [{'txid' : txidA}])

        self.log.info("Missing txid")
        assert_raises_rpc_error(-3, "Missing txid", self.nodes[0].gettxspendingprevout, [{'vout' : 3}])

        self.log.info("Test removetxfrommempool RPC")
        self.test_removetxfrommempool()

if __name__ == '__main__':
    RPCMempoolInfoTest(__file__).main()
