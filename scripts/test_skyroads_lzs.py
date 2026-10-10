"""Bounds and token edge cases complement the 31 original-code replay cases."""
import unittest
from skyroads_lzs import decode, LzsError


def stream(bits, widths=(3, 2, 3)):
    bits += '0' * (-len(bits) % 8)
    return bytes(widths) + int(bits or '0', 2).to_bytes(len(bits) // 8, 'big')


def literal(value):
    return '11' + f'{value:08b}'


class DecoderEdges(unittest.TestCase):
    def test_literal_msb_and_partial_byte(self):
        result = decode(stream(literal(0xa6)), 1)
        self.assertEqual(result.data, b'\xa6')
        self.assertEqual((result.meaningful_bits, result.consumed_bytes), (10, 5))

    def test_overlapping_short_match(self):
        bits = literal(65) + literal(66) + '0' + '00' + '011'
        self.assertEqual(decode(stream(bits), 7).data, b'ABABABA')

    def test_long_match_boundary(self):
        bits = ''.join(literal(v) for v in b'ABCDEF') + '10' + '000' + '000'
        self.assertEqual(decode(stream(bits), 8).data, b'ABCDEFAB')

    def test_rejects_truncated_literal(self):
        with self.assertRaises(LzsError):
            decode(bytes([3, 2, 3, 0xff]), 1)

    def test_rejects_backreference_before_start(self):
        with self.assertRaises(LzsError):
            decode(stream('0' + '00' + '000'), 2)

    def test_rejects_output_overrun(self):
        with self.assertRaises(LzsError):
            decode(stream(literal(65) + literal(66) + '0' + '00' + '111'), 3)

    def test_rejects_header_and_oversized_output(self):
        for data, length in [(b'\0\0', 1), (b'\x11\0\0', 1), (b'\0\0\0', 65536)]:
            with self.subTest(data=data, length=length), self.assertRaises(LzsError):
                decode(data, length)


if __name__ == '__main__':
    unittest.main()
