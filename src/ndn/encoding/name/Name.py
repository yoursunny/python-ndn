# -----------------------------------------------------------------------------
# Copyright (C) 2019 Xinyu Ma
#
# This file is part of python-ndn.
#
# python-ndn is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-ndn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with python-ndn.  If not, see <https://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
from functools import reduce
from typing import List, Optional, Iterable
from . import Component
from ..tlv_type import BinaryStr, VarBinaryStr, FormalName, NonStrictName, is_binary_str
from ..tlv_var import write_tl_num, parse_tl_num, get_tl_num_size


TYPE_NAME = 0x07


def from_str(val: str) -> List[bytearray]:
    # TODO: declare the differences: ":" and "."
    # Remove leading and tailing '/'
    cnt_slash = 0
    if val.startswith('/'):
        val = val[1:]
        cnt_slash += 1
    if val.endswith('/'):
        val = val[:-1]
        cnt_slash += 1
    if not val and cnt_slash <= 1:
        return []
    compstrs = val.split('/')
    return [Component.from_str(Component.escape_str(comp)) for comp in compstrs]


def to_str(name: NonStrictName) -> str:
    name = normalize(name)
    return '/' + '/'.join(Component.to_str(comp) for comp in name)


def from_bytes(buf: BinaryStr) -> FormalName:
    return decode(buf)[0]


def to_bytes(name: NonStrictName) -> bytes:
    if not is_binary_str(name):
        name = encode(normalize(name))
    return bytes(name)


def is_prefix(lhs: NonStrictName, rhs: NonStrictName) -> bool:
    lhs = normalize(lhs)
    rhs = normalize(rhs)
    left_len = len(lhs)
    return left_len <= len(rhs) and lhs == rhs[:left_len]


def encoded_length(name: FormalName) -> int:
    length = reduce(lambda x, y: x + len(y), name, 0)
    size_typ = 1
    size_len = get_tl_num_size(length)
    return length + size_typ + size_len


def encode(name: FormalName, buf: Optional[VarBinaryStr] = None, offset: int = 0) -> VarBinaryStr:
    length = reduce(lambda x, y: x + len(y), name, 0)
    size_typ = 1
    size_len = get_tl_num_size(length)

    if not buf:
        buf = bytearray(length + size_typ + size_len)
    else:
        if len(buf) < length + size_typ + size_len + offset:
            raise IndexError('buffer overflow')

    offset += write_tl_num(TYPE_NAME, buf, offset)
    offset += write_tl_num(length, buf, offset)
    for comp in name:
        buf[offset:offset+len(comp)] = comp
        offset += len(comp)
    return buf


def decode(buf: BinaryStr, offset: int = 0) -> (List[memoryview], int):
    buf = memoryview(buf)
    origin_offset = offset

    typ, size_typ = parse_tl_num(buf, offset)
    offset += size_typ
    if typ != TYPE_NAME:
        raise ValueError(f'the Type of {buf} is not Name')

    length, size_len = parse_tl_num(buf, offset)
    offset += size_len
    if length > len(buf) - offset:
        raise IndexError('buffer overflow')

    ret = []
    while length > 0:
        st = offset
        _, size_typ_comp = parse_tl_num(buf, offset)
        offset += size_typ_comp
        len_comp, size_len_comp = parse_tl_num(buf, offset)
        offset += size_len_comp + len_comp
        ret.append(buf[st:offset])
        length -= (offset - st)

    return ret, offset - origin_offset


def normalize(name: NonStrictName) -> FormalName:
    """
    Convert a NonStrictName to a FormalName.
    If name is a binary string, decode it.
    If name is a str, encode it into FormalName.
    If name is a list, encode all str elements into Components.

    :param name: the NonStrictName
    :type name: NonStrictName
    :return: the FormalName. It may be a swallow copy of name.
    :rtype: FormalName
    """
    if is_binary_str(name):
        return decode(name)[0]
    elif isinstance(name, str):
        return from_str(name)
    elif not isinstance(name, Iterable):
        raise TypeError('invalid type for name')
    ret = list(name)
    for i, comp in enumerate(ret):
        if isinstance(comp, str):
            ret[i] = Component.from_str(Component.escape_str(comp))
        elif not is_binary_str(comp):
            raise TypeError('invalid type for name component')
    return ret