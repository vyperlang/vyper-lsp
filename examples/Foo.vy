# @version ^0.3.8

event Foo:
    arg1: uint256
    arg2: address

struct Bar:
    x: uint256

enum Roles:
    ADMIN
    USER

m: Bar
n: Roles

FEE: constant(uint256) = 100

@external
def __init__():
    y: uint256 = FEE
    x: uint256 = FEE
    z: Bar = Bar({x: y})
    m: Roles = Roles.ADMIN
    log Foo(1, msg.sender)
    n: Roles = Roles.USER
    self.m = z
    self.n = n
    a: address = ZERO_ADDRESS
    self.m.x = 1
    log Foo(1, msg.sender)
    log Foo(1, msg.sender)

x: uint256

@external
def foo() -> uint256:
    return self.bar(10, 12)

@internal
def bar(x: uint256, y: uint256) -> uint256:
    return self.x + x + y

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
