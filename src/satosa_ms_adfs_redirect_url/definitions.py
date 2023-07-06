STATE_KEY = "REDIRURLCONTEXT"


class ADFSRedirectException(Exception):
    pass


class RelayStateMissingException(ADFSRedirectException):
    pass
