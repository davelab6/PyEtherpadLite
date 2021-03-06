#!/usr/bin/env python
"""Reverse engineered EtherpadLite Changeset API."""

import re
import string

def numToStr(num, b=36, numerals=string.digits + string.ascii_lowercase):
    """
    Converts integer num into a string representation on base b
    @param b {int} base to use
    @param numerals {string} characters used for string representation
    @returns {string} string representation of num in base b
    """
    # http://stackoverflow.com/questions/2267362/convert-integer-to-a-string-in-a-given-numeric-base-in-python
    return ((num == 0) and numerals[0]) \
            or (numToStr(num // b, b, numerals).lstrip(numerals[0]) + numerals[num % b])
def unpack(cs):
    """
    Unpacks a string encoded Changeset into a proper Changeset dict
    @param cs {string} String encoded Changeset
    @returns {dict} a Changeset class
    """
    header_regex = r"Z:([0-9a-z]+)([><])([0-9a-z]+)|"
    header_match = re.match(header_regex, cs)
    headers = header_match.groups()

    if header_match is None or len(headers) == 0:
        return dict()

    old_len     = int(headers[0], 36)
    change_sign = 1 if headers[1] == ">" else -1
    change_mag  = int(headers[2], 36)
    new_len     = old_len + change_sign * change_mag
    ops_start   = len(headers[0])+len(headers[1])+len(headers[2])
    ops_end     = cs.find("$")
    if ops_end < 0:
        ops_end = len(cs)
    return {
                "old_len": old_len,
                "new_len": new_len,
                "ops": cs[ops_start:ops_end],
                "char_bank": cs[ops_end+1:]
            }

def pack(csd):
    """
    Packs a Changeset dict into a string encoded Changeset
    @param cs {dict} a Changeset dict
    @returns {string} String encoded Changeset
    """
    len_diff = csd["new_len"] - csd["old_len"]
    len_diff_str = "<" + numToStr(len_diff) if len_diff >= 0 else "<" + numToStr(-len_diff)
    a = [ 'Z:', numToStr(csd["old_len"]), len_diff_str, "|", csd["ops"], "$", csd["char_bank"] ]
    return ''.join(a)


class Changeset:
    def __init__(self, attr):
        self._attribs = attr

    def apply_to_text(self, cs, txt):
        """
        Applies a Changeset to a string
        @params cs {string} String encoded Changeset
        @params str {string} String to which a Changeset should be applied
        """
        unpacked = unpack(cs)
        assert len(txt)+1 in (unpacked['old_len'], unpacked['old_len']+1)
        bank = unpacked['char_bank']
        bank_idx, txt_idx = (0, 0)
        for op in self.op_iterator(unpacked['ops']):
            if op["op_code"] == "+":
                txt.insert_at(txt_idx, bank[bank_idx:bank_idx+op["chars"]], op['attribs'])
                if not len(op['attribs']) is 0:
                    txt.set_attr(txt_idx, op['attribs'], op['chars'])
                bank_idx += op["chars"]
                txt_idx += op["chars"]
            elif op["op_code"] == "-":
                txt.remove(txt_idx, op["chars"])
            elif op["op_code"] == "=":
                if not len(op['attribs']) is 0:
                    txt.set_attr(txt_idx, op['attribs'], op['chars'])
                txt_idx += op["chars"]

    def op_iterator(self, opstr, op_start_idx=0):
        """
        this function creates an iterator which decodes string changeset operations
        @param opsStr {string} String encoding of the change operations to be performed
        @param optStartIndex {int} from where in the string should the iterator start
        @return {Op} type object iterator
        """
        regex = r"((?:\*[0-9a-z]+)*)(?:\|([0-9a-z]+))?([-+=\<\>])([0-9a-z]+)|\?|"
        start_idx = op_start_idx
        curr_idx  = start_idx
        prev_idx  = curr_idx
        last_idx  = 0
        match     = None
        has_next  = True
        regex_res = []

        prev_idx = curr_idx
        for match in re.finditer(regex, opstr):
            if match.start() != match.end():
                regex_res = match.groups()
                if regex_res[0] == '?':
                    print "Hit error opcode in op stream"
                    continue
                op = dict(attribs=regex_res[0],
                            lines=int(regex_res[1], 36) if not regex_res[1] is None else 0,
                          op_code=regex_res[2],
                            chars=int(regex_res[3], 36))
            else:
                op = dict(attribs='', lines=0, op_code='', chars=0)
            yield op
        return

