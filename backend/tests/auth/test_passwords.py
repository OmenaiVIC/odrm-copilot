from __future__ import annotations

from odrm.auth.passwords import PasswordHasher


def test_hash_differs_from_plaintext_and_verifies() -> None:
    hasher = PasswordHasher()
    password = "correct horse battery staple"

    hashed = hasher.hash(password)

    assert hashed != password
    assert hashed.startswith("$argon2")
    assert hasher.verify(password, hashed) is True


def test_wrong_password_fails() -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("correct horse battery staple")

    assert hasher.verify("wrong password", hashed) is False


def test_two_hashes_of_the_same_password_differ() -> None:
    hasher = PasswordHasher()
    password = "correct horse battery staple"

    assert hasher.hash(password) != hasher.hash(password)


def test_malformed_hash_fails_without_raising() -> None:
    hasher = PasswordHasher()

    assert hasher.verify("correct horse battery staple", "not-a-hash") is False


def test_dummy_verification_does_not_raise() -> None:
    hasher = PasswordHasher()

    hasher.verify_dummy("correct horse battery staple")
