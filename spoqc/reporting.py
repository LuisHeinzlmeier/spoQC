"""Plot settings scoped to one SpoQC invocation."""

from contextvars import ContextVar
from functools import wraps


_enabled = ContextVar("plots_enabled", default=True)


def plots_enabled():
    return _enabled.get()


def plots_only(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if plots_enabled():
            return function(*args, **kwargs)
    return wrapper


def configure_plots(function):
    @wraps(function)
    def wrapper(*args, plots=True, **kwargs):
        token = _enabled.set(plots)
        try:
            return function(*args, **kwargs)
        finally:
            _enabled.reset(token)
    return wrapper
