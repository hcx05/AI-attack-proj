from src.victim.tools.file_reader import read_file


def test_clean_faq_can_be_read():
    result = read_file("data/inputs/clean_faq.md")

    assert result["status"] == "allowed"
    assert result["content"] is not None
    assert "Clean" in result["content"] or "FAQ" in result["content"]


def test_mock_secret_is_blocked():
    result = read_file("data/secrets/mock_secret.txt")

    assert result["status"] == "blocked"
    assert result["content"] is None
    assert result["resolved_path"] is None


def test_path_traversal_to_secret_is_blocked():
    result = read_file("data/inputs/../secrets/mock_secret.txt")

    assert result["status"] == "blocked"
    assert result["content"] is None
    assert result["resolved_path"] is None


def test_missing_file_inside_inputs_returns_error():
    result = read_file("data/inputs/does_not_exist.md")

    assert result["status"] == "error"
    assert result["content"] is None
    assert "File not found" in result["error"]
