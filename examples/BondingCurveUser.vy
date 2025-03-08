#pragma version ^0.4.0

import BondingCurve

initializes: BondingCurve

x: uint256

s: constant(uint256) = 10**18

event Transfer:
    foo: address
    bar: uint256

flag Foo:
    BAR
    BAZ

struct FooStruct:
    foo: uint256
    bar: uint256

@deploy
def __init__(shares_name: String[25], shares_symbol: String[5], shares_decimals: uint8):
    foo: Foo = Foo.BAR
    foo_s: FooStruct = FooStruct(foo=1, bar=2)
    BondingCurve.__init__(0, 2, 10**18, 16000)
