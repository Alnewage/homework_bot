class RequiredEnvVariables(Exception):
    def __init__(self, message):
        super().__init__(message)


class StatusCodeError(Exception):
    def __init__(self, message):
        super().__init__(message)


class VerdictError(Exception):
    def __init__(self, message):
        super().__init__(message)