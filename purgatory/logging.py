"""Setup logging for Purgatory."""


import inspect
import logging
import sys
import traceback


class ModFuncFilter(logging.Filter):
    """Logging filter to combine module and funcName as modfunc.

    This allows to have <module>.<func.-name> or <module>.<class>.<method-name>
    with a fixed width.  If the module starts with 'purgatory.' or 'tests.'
    then the prefix will be stripped.

    Example: %(modfunc)-50s
    """
    def filter(self, record):
        stack = inspect.stack()
        # Unwind stack until the logging module has been left to get the caller
        # information.  Start with the second stack segment as the first is
        # this filter method.
        for segment in enumerate(stack[1:]):
            caller_frame = segment[1][0]
            caller_module = inspect.getmodule(caller_frame)
            caller_module_name = caller_module.__name__
            if caller_module_name != "logging":
                break  # Found the caller.

        # If the module name starts with 'purgatory.' or 'tests.' then strip
        # it.  Note: len("purgatory.") == 10; len("tests.") == 6
        if caller_module_name.startswith("purgatory."):
            caller_module_name = caller_module_name[10:]
        if caller_module_name.startswith("tests."):
            caller_module_name = caller_module_name[6:]

        # Get all the needed information from the caller traceback.
        caller_traceback = inspect.getframeinfo(caller_frame)
        caller_function_name = caller_traceback.function
        caller_local_variables = caller_frame.f_locals
        caller_class_name = None
        if "self" in caller_local_variables:
            # Looks like a method or property call.
            caller_self = caller_local_variables["self"]
            caller_class = caller_self.__class__
            caller_class_name = caller_class.__name__

        # Register modfunc.
        if caller_class_name:
            record.modfunc = ".".join((
                caller_module_name, caller_class_name, caller_function_name))
        else:  # pragma: no cover
            record.modfunc = ".".join((
                caller_module_name, caller_function_name))
        return True


def configure_root_logger_for_debug():
    """(Re)configures logging for debugging.

    As logging hasn't been fully set up at this point this function prints a
    traceback to stderr in case of an exception.
    """
    try:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

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


def init_cli_logging(debug=False):  # pragma: no cover
    """Initializes logging for the command line interface.

    All log output will be redirected to stderr so that users can easily
    silence/ignore the log messages by pipping stderr to /dev/null.

    Args:
        debug: Enabled debug logging. By default False.
    """
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=logging.INFO,
        stream=sys.stderr)
    if debug:
        configure_root_logger_for_debug()
