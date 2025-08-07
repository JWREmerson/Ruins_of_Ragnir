# External Imports
import logging

def setup_logging(level=logging.INFO):
    logging.basicConfig(format='[%(levelname)s] %(message)s', level=level)
def validate_positive(value: int) -> bool:
    return isinstance(value, int) and value >= 0
def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)