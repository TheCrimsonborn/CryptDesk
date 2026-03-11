import unittest

from cryptography.exceptions import InvalidTag

from cryptdesk.crypto import derive_session, generate_identity
from cryptdesk.protocol import decode_packet, encode_packet


class CryptoTests(unittest.TestCase):
    def test_session_roundtrip(self) -> None:
        host_identity = generate_identity()
        viewer_identity = generate_identity()
        host_session = derive_session(host_identity.private_key, viewer_identity.public_key_b64, "host", "secret")
        viewer_session = derive_session(viewer_identity.private_key, host_identity.public_key_b64, "viewer", "secret")
        plaintext = b"cryptdesk-handshake"
        self.assertEqual(host_session.safety_code, viewer_session.safety_code)
        self.assertEqual(viewer_session.decrypt(host_session.encrypt(plaintext)), plaintext)
        self.assertEqual(host_session.decrypt(viewer_session.encrypt(plaintext)), plaintext)

    def test_protocol_roundtrip(self) -> None:
        packet = encode_packet({"type": "frame", "width": 640, "height": 360}, b"payload")
        header, payload = decode_packet(packet)
        self.assertEqual(header["type"], "frame")
        self.assertEqual(header["width"], 640)
        self.assertEqual(payload, b"payload")

    def test_mismatched_passphrases_fail_session_decryption(self) -> None:
        host_identity = generate_identity()
        viewer_identity = generate_identity()
        host_session = derive_session(host_identity.private_key, viewer_identity.public_key_b64, "host", "alpha")
        viewer_session = derive_session(viewer_identity.private_key, host_identity.public_key_b64, "viewer", "beta")

        self.assertNotEqual(host_session.safety_code, viewer_session.safety_code)
        with self.assertRaises(InvalidTag):
            viewer_session.decrypt(host_session.encrypt(b"cryptdesk-handshake"))


if __name__ == "__main__":
    unittest.main()
