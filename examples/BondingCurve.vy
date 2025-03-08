# version ^0.4.0
"""
@title Bonding Curve Functions
@custom:contract-name BondingCurve
@license MIT License
@author z80
@notice These functions can be used to implement a basic bonding curve
"""
current_step: uint256
EXPONENT: immutable(uint256)
SCALING_FACTOR: immutable(uint256)
TICK_SIZE: immutable(uint256)

@deploy
def __init__(start_step: uint256, exponent: uint256, scaling_factor: uint256, tick_size: uint256):
    self.current_step = start_step
    EXPONENT = exponent
    SCALING_FACTOR = scaling_factor
    TICK_SIZE = tick_size

@view
@internal
def _get_current_price() -> uint256:
    """
    Returns the current price of the token
    """
    current_step_exp: uint256 = pow_mod256(self.current_step, EXPONENT)
    return current_step_exp * SCALING_FACTOR // TICK_SIZE

@view
@internal
def _get_price_at_step(step: uint256) -> uint256:
    """
    Returns the price of the token at a given step
    """
    step_exp: uint256 = pow_mod256(step, EXPONENT)
    return step_exp * SCALING_FACTOR // TICK_SIZE

@internal
def _increment_step():
    """
    Increments the current step by 1
    """
    self.current_step += 1

@internal
def _decrement_step():
    """
    Decrements the current step by 1
    """
    self.current_step -= 1

@internal
def _set_step(step: uint256):
    """
    Sets the current step to a given value
    """
    self.current_step = step
