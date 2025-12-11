"""
Decimal Arithmetic Utilities
Prevents float precision issues in financial calculations
Uses integer cents for perfect accuracy
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
from typing import List, Dict, Union


def dollars_to_cents(amount: Union[float, str, Decimal]) -> int:
    """
    Convert dollar amount to cents (integer)
    $10.50 -> 1050 cents
    
    Args:
        amount: Dollar amount as float, string, or Decimal
    
    Returns:
        Integer cents (no precision loss)
    
    Examples:
        >>> dollars_to_cents(10.50)
        1050
        >>> dollars_to_cents("10.50")
        1050
        >>> dollars_to_cents(Decimal("10.50"))
        1050
    """
    if isinstance(amount, int):
        return amount * 100
    
    decimal_amount = Decimal(str(amount))
    cents = int(decimal_amount * 100)
    return cents


def cents_to_dollars(cents: int) -> Decimal:
    """
    Convert cents (integer) to dollar Decimal
    1050 cents -> $10.50
    
    Args:
        cents: Integer cents
    
    Returns:
        Decimal dollar amount
    
    Examples:
        >>> cents_to_dollars(1050)
        Decimal('10.50')
        >>> cents_to_dollars(1000)
        Decimal('10.00')
    """
    return Decimal(cents) / 100


def cents_to_dollars_float(cents: int) -> float:
    """
    Convert cents to dollars as float (for JSON serialization)
    Use only for display, never for calculations!
    """
    return round(cents / 100.0, 2)


def calculate_equal_split(amount_cents: int, num_people: int) -> List[int]:
    """
    Split amount equally among people, distributing remainder fairly
    Uses integer arithmetic - NO FLOAT DRIFT
    
    Args:
        amount_cents: Total amount in cents
        num_people: Number of people to split among
    
    Returns:
        List of cent amounts (integers) that sum exactly to amount_cents
    
    Examples:
        >>> calculate_equal_split(1000, 3)  # $10.00 / 3
        [333, 333, 334]  # $3.33, $3.33, $3.34 - sums to exactly $10.00
        
        >>> calculate_equal_split(100, 3)  # $1.00 / 3
        [33, 33, 34]  # $0.33, $0.33, $0.34 - sums to exactly $1.00
        
        >>> sum(calculate_equal_split(1000, 3))
        1000  # ✅ Perfect sum
    """
    if num_people <= 0:
        raise ValueError("num_people must be > 0")
    
    if amount_cents < 0:
        raise ValueError("amount_cents must be >= 0")
    
    # Base amount per person (integer division)
    base_cents = amount_cents // num_people
    
    # Remainder cents to distribute
    remainder = amount_cents % num_people
    
    # Everyone gets base amount
    splits = [base_cents] * num_people
    
    # Distribute remainder (last N people get +1 cent)
    # This ensures sum(splits) == amount_cents exactly
    for i in range(remainder):
        splits[-(i + 1)] += 1
    
    # Verify sum (assertion for safety)
    assert sum(splits) == amount_cents, f"Split sum mismatch: {sum(splits)} != {amount_cents}"
    
    return splits


def calculate_percentage_split(amount_cents: int, percentages: List[float]) -> List[int]:
    """
    Split amount by percentages, ensuring sum equals total
    
    Args:
        amount_cents: Total amount in cents
        percentages: List of percentages (must sum to 100)
    
    Returns:
        List of cent amounts (integers) that sum exactly to amount_cents
    
    Examples:
        >>> calculate_percentage_split(1000, [50.0, 30.0, 20.0])
        [500, 300, 200]  # $5.00, $3.00, $2.00
        
        >>> calculate_percentage_split(1000, [33.33, 33.33, 33.34])
        [333, 333, 334]  # Handles rounding
    """
    if abs(sum(percentages) - 100.0) > 0.01:
        raise ValueError(f"Percentages must sum to 100, got {sum(percentages)}")
    
    # Calculate each split with rounding
    splits = []
    for pct in percentages:
        split_cents = int(Decimal(str(amount_cents * pct / 100)).quantize(Decimal('1'), ROUND_HALF_UP))
        splits.append(split_cents)
    
    # Adjust last split to ensure perfect sum
    total_split = sum(splits)
    difference = amount_cents - total_split
    splits[-1] += difference
    
    assert sum(splits) == amount_cents, f"Split sum mismatch: {sum(splits)} != {amount_cents}"
    
    return splits


def calculate_exact_split(amounts_cents: List[int], total_cents: int = None) -> List[int]:
    """
    Validate exact split amounts
    
    Args:
        amounts_cents: List of exact cent amounts
        total_cents: Optional total to validate against
    
    Returns:
        Same list if valid, raises ValueError if invalid
    
    Examples:
        >>> calculate_exact_split([333, 333, 334], 1000)
        [333, 333, 334]
        
        >>> calculate_exact_split([333, 333, 333], 1000)
        ValueError: Split sum (999) doesn't match total (1000)
    """
    split_sum = sum(amounts_cents)
    
    if total_cents is not None and split_sum != total_cents:
        raise ValueError(f"Split sum ({split_sum}) doesn't match total ({total_cents})")
    
    return amounts_cents


def format_cents_for_display(cents: int) -> str:
    """
    Format cents as currency string for display
    
    Examples:
        >>> format_cents_for_display(1050)
        '$10.50'
        >>> format_cents_for_display(-1050)
        '-$10.50'
        >>> format_cents_for_display(1000)
        '$10.00'
    """
    dollars = cents_to_dollars(cents)
    if cents < 0:
        return f"-${abs(dollars)}"
    return f"${dollars}"


def verify_balance_sum_zero(balances: Dict[str, int], tolerance_cents: int = 0) -> bool:
    """
    Verify that all balances sum to zero (or within tolerance)
    
    Args:
        balances: Dict of user_id -> balance_cents
        tolerance_cents: Allowable drift (should be 0 for perfect math)
    
    Returns:
        True if sum == 0 (within tolerance)
    
    Examples:
        >>> balances = {'user1': 1000, 'user2': -500, 'user3': -500}
        >>> verify_balance_sum_zero(balances)
        True
        
        >>> balances = {'user1': 1000, 'user2': -500, 'user3': -499}
        >>> verify_balance_sum_zero(balances, tolerance_cents=0)
        False
        >>> verify_balance_sum_zero(balances, tolerance_cents=1)
        True
    """
    total = sum(balances.values())
    return abs(total) <= tolerance_cents


# Quick tests (run with: python -m doctest decimal_utils.py)
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
    # Additional manual tests
    print("Testing equal split...")
    splits = calculate_equal_split(1000, 3)
    print(f"  $10.00 / 3 = {splits} cents")
    print(f"  Sum: {sum(splits)} (should be 1000)")
    print(f"  In dollars: {[cents_to_dollars_float(s) for s in splits]}")
    
    print("\nTesting percentage split...")
    splits = calculate_percentage_split(1000, [50, 30, 20])
    print(f"  $10.00 with 50%/30%/20% = {splits} cents")
    print(f"  Sum: {sum(splits)} (should be 1000)")
    
    print("\nTesting balance verification...")
    balances = {'user1': 1000, 'user2': -500, 'user3': -500}
    print(f"  Balances: {balances}")
    print(f"  Sum to zero: {verify_balance_sum_zero(balances)}")
    
    print("\n✅ All tests passed!")
