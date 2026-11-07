import io
import unittest

from mutagen.id3 import ID3, TALB, TENC, TIT2, TPE1, TSIZ, TSSE

import main


def make_id3(*, size="16", iv="00112233445566778899aabbccddeeff"):
    tag = ID3()
    tag.add(TIT2(encoding=3, text="title"))
    tag.add(TALB(encoding=3, text="album"))
    tag.add(TPE1(encoding=3, text="artist"))
    tag.add(TSIZ(encoding=3, text=size))
    tag.add(TSSE(encoding=3, text="A"))
    tag.add(TENC(encoding=3, text=iv))
    output = io.BytesIO()
    tag.save(output, v2_version=3)
    return output.getvalue()


class XmInputValidationTests(unittest.TestCase):
    def test_rejects_non_id3_input_with_actionable_message(self):
        with self.assertRaisesRegex(ValueError, "不是 ID3v2 标签"):
            main.get_xm_info(b"not an xm file")

    def test_rejects_malformed_id3_input_with_actionable_message(self):
        with self.assertRaisesRegex(ValueError, "缺少必要的 ID3 元数据"):
            main.get_xm_info(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    def test_rejects_truncated_encrypted_payload(self):
        header = make_id3(size="32")
        with self.assertRaisesRegex(ValueError, "加密数据长度无效"):
            main.get_xm_info(header + b"short")

    def test_rejects_invalid_aes_iv(self):
        header = make_id3(size="16", iv="00")
        with self.assertRaisesRegex(ValueError, "AES 初始向量长度无效"):
            main.get_xm_info(header + b"0" * 16)


if __name__ == "__main__":
    unittest.main()
