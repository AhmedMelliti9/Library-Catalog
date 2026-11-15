"""
exceptions.py
Domain-level exceptions raised by repositories and services.
Routes catch these and convert them to the correct HTTP responses.
"""


class BookNotFoundError(Exception):
    pass


class AuthorNotFoundError(Exception):
    pass


class BookAlreadyCheckedOutError(Exception):
    pass


class BookNotCheckedOutError(Exception):
    pass


class DuplicateISBNError(Exception):
    pass


class InvalidAuthorError(Exception):
    pass
