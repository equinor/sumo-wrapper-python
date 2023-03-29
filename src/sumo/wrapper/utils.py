import jwt


def decode_jwt_token(self, token: str) -> dict:
    """
    Decodes a Json Web Token, returns the payload as a dictionary.

    Args:
        token: Token to decode

    Returns:
        Decoded Json Web Token (None if token can't be decoded)
    """

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except jwt.InvalidTokenError:
        return None
