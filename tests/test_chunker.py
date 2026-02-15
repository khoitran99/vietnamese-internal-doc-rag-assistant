import unittest

from src.indexing.chunker import build_chunks, extract_section_blocks


class TestChunker(unittest.TestCase):
    def test_extract_section_blocks(self) -> None:
        text = "# HR\n## Leave\nNhan vien nghi phep.\n## Overtime\nLam them duoc phe duyet."
        blocks = extract_section_blocks(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].section_path, "HR > Leave")
        self.assertEqual(blocks[1].section_path, "HR > Overtime")

    def test_build_chunks_deterministic(self) -> None:
        text = "# A\n" + " ".join(["token"] * 120)
        chunks1 = build_chunks(
            doc_id="doc1",
            title="Doc 1",
            text=text,
            department="General",
            updated_at="1970-01-01",
            access_level="public",
            chunk_size_tokens=50,
            overlap_tokens=10,
        )
        chunks2 = build_chunks(
            doc_id="doc1",
            title="Doc 1",
            text=text,
            department="General",
            updated_at="1970-01-01",
            access_level="public",
            chunk_size_tokens=50,
            overlap_tokens=10,
        )
        self.assertEqual([c.chunk_id for c in chunks1], [c.chunk_id for c in chunks2])


if __name__ == "__main__":
    unittest.main()
