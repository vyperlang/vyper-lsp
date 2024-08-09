#pragma version ^0.4.0

event Foo:
    arg1: uint256
    arg2: address

struct Bar:
    x: uint256

flag Roles:
    ADMIN
    USER

m: Bar
n: Roles

FEE: constant(uint256) = 100

@deploy
def __init__():
    y: uint256 = 100_000_100
    x: uint256 = FEE
    z: Bar = Bar(x=y)
    m: Roles = Roles.ADMIN
    log Foo(1, msg.sender)
    n: Roles = Roles.USER
    self.m = z
    self.n = n
    a: address = empty(address)
    self.m.x = 1
    log Foo(1, msg.sender)
    log Foo(1, msg.sender)

@external
def foo() -> uint256:
    return self.bar(10, 12)[0]

x: uint256

@internal
def bar(x: uint256, y: uint256) -> uint256[2]:
    return [self.x + x + y, x]

@external
def baz(a: uint256, b: uint256) -> Bar:
    return self.m

_owner: address

interface Ownable:
    # get address of owner
    def owner() -> address: view

implements: Ownable

@view
@external
def owner() -> address:
    return self._owner

N_COINS: constant(uint256) = 2
A_MULTIPLIER: constant(uint256) = 10000

MIN_A: constant(uint256) = N_COINS**N_COINS * A_MULTIPLIER // 10
