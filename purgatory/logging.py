"""Setup logging for Purgatory."""

import logging
import sys
import traceback


class ModFuncFilter(logging.Filter):
    """Logging filter to combine module and funcName as modfunc.

    This allows to have <module>.<function-name> with a fixed width.
    Example: %(modfunc)-50s
    """
    def filter(self, record):
        record.modfunc = record.module + "." + record.funcName
        return True


def configure_root_logger():
    """(Re)configures logging.

    As logging hasn't been fully set up at this point this function prints a
    traceback to stderr in case of an exception.
    """
    try:
        root_logger = logging.getLogger()

        # Add the ModFuncFilter if it isn't present yet.
        found = False
        for filter_ in root_logger.filters:
            if filter_.__class__ == ModFuncFilter:
                found = True
        if not found:
            root_logger.addFilter(ModFuncFilter())

        # Set logger format of all handlers.
        fmt = ("%(relativeCreated)10.2f %(levelname)-8s %(modfunc)-50s | "
               "%(message)s")
        formatter = logging.Formatter(fmt=fmt)
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)

    except:  # pragma: no cover
        print(traceback.format_exc(), file=sys.stderr)
        raise
