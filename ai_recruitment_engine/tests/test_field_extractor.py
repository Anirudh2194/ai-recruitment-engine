from app.modules.resume_parser.field_extractor import extract_email, extract_name


def test_extract_email_found():
    text = "John Doe\nSoftware Engineer\njohn.doe@example.com\n+1 555-0100"
    assert extract_email(text) == "john.doe@example.com"


def test_extract_email_missing():
    assert extract_email("No contact info here") is None


def test_extract_name_first_line():
    text = "Jane Smith\nData Scientist\njane@example.com"
    assert extract_name(text, "resume.pdf") == "Jane Smith"


def test_extract_name_falls_back_to_filename():
    text = "1234567890\nsome garbled OCR text with no clean name line and way too many words here"
    assert extract_name(text, "priya_kumar.pdf") == "Priya Kumar"
