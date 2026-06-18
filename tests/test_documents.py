import pytest
import responses

from apps.tenders.models import Tender, TenderDocument
from apps.tenders.services import download_document

pytestmark = pytest.mark.django_db


def _doc(eis_source, url="https://example.com/tz.pdf"):
    tender = Tender.objects.create(source=eis_source, external_id="T1", title="t")
    return TenderDocument.objects.create(tender=tender, url=url, title="TZ")


@responses.activate
def test_download_document_stores_file(eis_source):
    doc = _doc(eis_source)
    responses.add(
        responses.GET, doc.url, body=b"%PDF-1.4 fake content",
        content_type="application/pdf", status=200,
    )
    assert download_document(doc) is True
    doc.refresh_from_db()
    assert doc.is_downloaded is True
    assert doc.file_size == len(b"%PDF-1.4 fake content")
    assert doc.content_type == "application/pdf"
    assert doc.file.read() == b"%PDF-1.4 fake content"
    doc.file.delete(save=False)  # cleanup


@responses.activate
def test_download_document_records_error_on_failure(eis_source):
    doc = _doc(eis_source, url="https://example.com/missing.pdf")
    responses.add(responses.GET, doc.url, status=404)
    assert download_document(doc) is False
    doc.refresh_from_db()
    assert doc.is_downloaded is False
    assert doc.download_error


@responses.activate
def test_download_uses_real_title_as_filename(eis_source):
    # EIS filestore URLs end in 'file.html'; the real name lives in the title.
    doc = _doc(eis_source, url="https://zakupki.gov.ru/44fz/filestore/.../file.html?uid=ABC")
    doc.title = "Обоснование НМЦК.xlsx"
    doc.save()
    responses.add(responses.GET, doc.url, body=b"data", status=200)
    assert download_document(doc) is True
    doc.refresh_from_db()
    assert doc.file.name.endswith(".xlsx")
    assert "file.html" not in doc.file.name
    doc.file.delete(save=False)


@responses.activate
def test_download_document_respects_size_limit(eis_source, settings):
    settings.DOCUMENT_MAX_BYTES = 10
    doc = _doc(eis_source, url="https://example.com/big.pdf")
    responses.add(responses.GET, doc.url, body=b"x" * 50, status=200)
    assert download_document(doc) is False
    doc.refresh_from_db()
    assert doc.is_downloaded is False
    assert "exceeds" in doc.download_error
