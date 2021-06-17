#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Split up large trees into smaller subtrees plus one supertree linking the subtrees
For the SHOOT database rooted trees are required (i.e. Gene_Tree/ directory of Orthofinder)
so translate these back to OrthoFinder IDs using the -w option

"""
import os 
import argparse

import ete3

import fasta_writer

def split_tree(fn_tree, fn_msa, n_taxa, q_outgroup, q_ids=False):
    """
    Split a tree into smaller subtrees
    Args:
        fn_tree - input tree filename
        fn_msa - input MSA filename
        n_taxa - number of taxa to aim for in each sub tree
        q_outgroup - include an outgroup taxon in each subtree to allow downstream root placement
    Returns:
        n - number of profile sequences required
    Implementation:
        Each tree with more than 5 sequences requires 5 profile sequences. Below 
        that, it is the number of sequences in the tree.
        Clades left in the tree are treated as requiring 5 profile sequences too.
    """
    fw = fasta_writer.FastaWriter(fn_msa)
    # if q_ids:
    #     import ofids
    #     ids = ofids.OrthoFinderIDs(os.path.dirname + "/../WorkingDirectory/").Spec_SeqDict()
    #     ids_rev = {v:k for k,v in ids.items()}
    if q_outgroup:
        # work out number of gaps for each gene - cheap measure of what's best
        # to use as the outgroup gene
        d_ngaps = {name:seq.count("-") for name, seq in fw.SeqLists.items()}
    n_profile = 0
    d, fn = os.path.split(fn_tree)
    if d == "":
        d = "./"
    dout_main = d + "/subtrees/"
    d_out_sup = dout_main + "super/"
    d_out_sub = dout_main + "sub/"
    d_out_msa_sub = dout_main + "msa_sub/"
    for d_to_make in [dout_main, d_out_sup, d_out_sub, d_out_msa_sub]:
        if not os.path.exists(d_to_make):
            os.mkdir(d_to_make)
    t = ete3.Tree(fn_tree)
    fn_out_pat = d_out_sub + fn + ".%d.tre"
    fn_out_msa_pat = d_out_msa_sub + fn + ".%d.fa"
    fn_out_mega_pat = d_out_sup + fn + ".super.tre"
    i_part = 0
    if len(t) <= n_taxa:
        t.write(outfile = fn_out_pat % i_part)
        # print("No need to split tree")
        return min(5, len(t))
    # traverse tree
    sizes = []
    stop_fn = lambda node : len(node) <= n_taxa
    for n in t.traverse("preorder", is_leaf_fn = stop_fn):
        l = len(n)
        if l <= n_taxa:
            # Steps:
            # 1. Write newick & MSA for subtree
            # 2. Name the node in the supertree to PART...
            # 3. Reread in subtree and unroot if required (don't mess around with the original tree)
            # 4. After we've finished, remove all the subtrees below the PART... nodes
            n_profile += min(5, l)
            if not q_outgroup:
                nwk = n.write(outfile)
                fw.WriteSeqsToFasta(n.get_leaf_names(), fn_out_msa_pat % i_part)
            else:    
                # go to sister clade, pick gene with fewest gaps
                sisters = [s for s in n.up.children if s != n]
                sister_genes = [g for s in sisters for g in s.get_leaf_names()]
                n_gaps = [9e99 if g.startswith("PART.") else d_ngaps[g] for g in sister_genes]
                x = min(n_gaps)
                i = n_gaps.index(x)   # doesn't matter if there is a tie, any will do
                outgrp = sister_genes[i]
                d = n.get_distance(outgrp)
                if not (d > n.dist):
                    print(([n, ], sisters))
                    print((n.get_leaf_names()[0], outgrp))
                    print((n.dist, d))
                assert(d > n.dist)
                nwk = n.write()
                nwk = "(" + nwk[:-1] + ",SHOOTOUTGROUP_%s:%0.5f);" % (outgrp, d-n.dist)
                genes = n.get_leaf_names()
                translate = {g:g for g in genes}
                translate[outgrp] = "SHOOTOUTGROUP_" + outgrp
                fw.WriteSeqsToFasta(genes, fn_out_msa_pat % i_part)
            with open(fn_out_pat % i_part, 'w') as outfile:
                outfile.write(nwk + "\n")
            n.name = "PART.%d-%d_genes" % (i_part, l)
            sizes.append(l)
            t_sub = ete3.Tree(nwk)
            if len(t_sub) >= 3:
                t_sub.unroot()
            t_sub.write(outfile = (fn_out_pat % i_part) + ".unroot.tre")
            i_part += 1
    # 4. Remove all the subtrees
    for n in t.traverse('preorder', is_leaf_fn=stop_fn):
        if n.name.startswith("PART."):
            for ch in n:
                ch.detach()
    # print(sorted(sizes))
    t.write(outfile=fn_out_mega_pat)
    t.unroot()
    t.write(outfile=fn_out_mega_pat + ".unroot.tre")
    # print(fn_out_mega_pat)
    return n_profile

def count_profiles():
    n_target_taxa = 500
    d = "/lv01/data/emms/SHOOT/DATA/UniProt_RefProteomes_homologs/"
    fn_tree_pat = d + "Gene_Trees/OG%07d_tree.txt"
    fn_msa_pat = d + "MultipleSequenceAlignments/OG%07d.fa"
    n_trees = 17125
    n_profiles = 0
    for i in range(n_trees):
        if i % 100 == 0:
            print(i)
        n_profiles += split_tree(fn_tree_pat % i, fn_msa_pat % i, n_target_taxa)
    print("%d profile sequences required" % n_profiles)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tree", help="Input tree file")
    parser.add_argument("msa", help="Input MSA file")
    parser.add_argument("-n", "--ntaxa", help="Number of taxa to aim for for each subtree", type=int, default=500)
    parser.add_argument("-i", "--ids", action="store_true",
                        help="Translate back to OrthoFinder IDs")
    parser.add_argument("-o", "--outgroup", action="store_true",
                        help="Include an outgroup gene in each subtree. Required for SHOOT", )
    args = parser.parse_args()
    split_tree(args.tree, 
                args.msa, 
                args.ntaxa, 
                q_outgroup=args.outgroup,
                q_ids=args.ids)

    # count_profiles()