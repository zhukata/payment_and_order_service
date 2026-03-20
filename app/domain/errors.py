class DomainError(Exception):
    """Base domain error."""


class NotFoundError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class PaymentLimitExceededError(DomainError):
    pass


class InvalidPaymentStateError(DomainError):
    pass


class ExternalServiceError(DomainError):
    pass
