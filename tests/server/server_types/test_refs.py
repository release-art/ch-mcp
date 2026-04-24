"""Tests for URL-id extraction and per-resource refs types."""

import pytest

from ch_mcp.server.types import refs


class TestParseUrlIds:
    def test_company_self_link(self):
        assert refs.parse_url_ids("/company/09370755") == {"company_number": "09370755"}

    def test_company_with_trailing_slash(self):
        assert refs.parse_url_ids("/company/SC123456/") == {"company_number": "SC123456"}

    def test_charge(self):
        got = refs.parse_url_ids("/company/09370755/charges/abc-charge-id")
        assert got == {"company_number": "09370755", "charge_id": "abc-charge-id"}

    def test_appointment(self):
        got = refs.parse_url_ids("/company/09370755/appointments/XYZAPPT")
        assert got == {"company_number": "09370755", "appointment_id": "XYZAPPT"}

    def test_filing_history_item(self):
        got = refs.parse_url_ids("/company/09370755/filing-history/txn-999")
        assert got == {"company_number": "09370755", "transaction_id": "txn-999"}

    def test_psc_individual(self):
        got = refs.parse_url_ids("/company/09370755/persons-with-significant-control/individual/pscABC")
        assert got == {
            "company_number": "09370755",
            "psc_url_kind": "individual",
            "psc_id": "pscABC",
        }

    def test_psc_statement(self):
        got = refs.parse_url_ids("/company/09370755/persons-with-significant-control-statements/stmt42")
        assert got == {"company_number": "09370755", "psc_statement_id": "stmt42"}

    def test_officer_appointments_list(self):
        got = refs.parse_url_ids("/officers/OFF123/appointments")
        assert got == {"officer_id": "OFF123"}

    def test_natural_disqualification(self):
        got = refs.parse_url_ids("/disqualified-officers/natural/DISQ1")
        assert got == {"officer_id": "DISQ1", "disqualification_kind": "natural"}

    def test_corporate_disqualification(self):
        got = refs.parse_url_ids("/disqualified-officers/corporate/DISQ2")
        assert got == {"officer_id": "DISQ2", "disqualification_kind": "corporate"}

    def test_document(self):
        got = refs.parse_url_ids("https://document-api.company-information.service.gov.uk/document/L_X0y9bwYnkyEMwL")
        assert got == {"document_id": "L_X0y9bwYnkyEMwL"}

    def test_empty(self):
        assert refs.parse_url_ids("") == {}

    def test_no_match(self):
        assert refs.parse_url_ids("https://example.com/random/path") == {}


class TestExtractRefs:
    def test_filing_history_with_document(self):
        links = {
            "self": "/company/09370755/filing-history/txn-42",
            "document_metadata": "https://document-api.company-information.service.gov.uk/document/DOCID",
        }
        got = refs.extract_refs(refs.FilingHistoryItemRefs, links)
        assert got.company_number == "09370755"
        assert got.transaction_id == "txn-42"
        assert got.document_id == "DOCID"

    def test_filing_history_without_document(self):
        links = {"self": "/company/09370755/filing-history/txn-42"}
        got = refs.extract_refs(refs.FilingHistoryItemRefs, links)
        assert got.document_id is None

    def test_psc_list_item(self):
        links = {
            "self": "/company/09370755/persons-with-significant-control/individual/pscX",
        }
        got = refs.extract_refs(refs.PscListItemRefs, links)
        assert got.company_number == "09370755"
        assert got.psc_id == "pscX"

    def test_officer_list_item_with_officer_cross_ref(self):
        links = {
            "self": "/company/09370755/appointments/ap1",
            "officer": {"appointments": "/officers/OFF1/appointments"},
        }
        # Flatten: parse_url_ids only reads string values at the top level of
        # the mapping. Nested dicts like "officer" are not traversed.
        got = refs.extract_refs(refs.OfficerListItemRefs, links)
        assert got.company_number == "09370755"
        assert got.appointment_id == "ap1"
        # officer_id is Optional and the nested dict isn't walked, so it stays None.
        assert got.officer_id is None

    def test_officer_appointment_item_company_only(self):
        # Items on /officers/{id}/appointments carry only links.company — no
        # self link, no appointment_id. Regression: earlier required
        # appointment_id broke every get_officer_appointments call.
        links = {"company": "/company/15913627"}
        got = refs.extract_refs(refs.OfficerAppointmentItemRefs, links)
        assert got.company_number == "15913627"

    def test_disqualification(self):
        links = {"self": "/disqualified-officers/natural/OFF1"}
        got = refs.extract_refs(refs.DisqualificationRefs, links)
        assert got.officer_id == "OFF1"

    def test_charge_details(self):
        links = {"self": "/company/09370755/charges/charge-7"}
        got = refs.extract_refs(refs.ChargeDetailsRefs, links)
        assert got.company_number == "09370755"
        assert got.charge_id == "charge-7"

    def test_document_metadata(self):
        links = {
            "self": "/document/DOC1",
            "document": "https://document-api.company-information.service.gov.uk/document/DOC1/content",
        }
        got = refs.extract_refs(refs.DocumentMetadataRefs, links)
        assert got.document_id == "DOC1"

    def test_missing_required_field_raises(self):
        # company_number is required but the link set lacks it
        with pytest.raises(Exception):  # noqa: B017 — pydantic.ValidationError
            refs.extract_refs(refs.ChargeDetailsRefs, {"self": "/something-unrelated"})

    def test_empty_links_dict(self):
        with pytest.raises(Exception):  # noqa: B017
            refs.extract_refs(refs.CompanyProfileRefs, {})
