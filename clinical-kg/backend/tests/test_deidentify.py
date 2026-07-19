"""De-identification (Safe Harbor) tests."""

from __future__ import annotations

from clinical_kg.deidentify import SurrogateVault, deidentify, reidentify


def test_redacts_common_phi():
    text = "John Smith, MRN: 4483920, phone (617) 555-0142, seen on 03/14/2025, email j@x.com."
    result = deidentify(text)
    assert "4483920" not in result.text
    assert "555-0142" not in result.text
    assert "03/14/2025" not in result.text
    assert "j@x.com" not in result.text
    assert result.replacements >= 4


def test_redacts_ssn_and_url():
    text = "SSN 123-45-6789 see http://records.example.com/patient"
    result = deidentify(text)
    assert "123-45-6789" not in result.text
    assert "http://records.example.com/patient" not in result.text


def test_reidentify_round_trips():
    vault = SurrogateVault()
    text = "Contact patient at (617) 555-0142 on 03/14/2025."
    result = deidentify(text, vault)
    restored = reidentify(result.text, vault, result.vault_id)
    assert restored == text


def test_vault_is_sealed_by_id():
    vault = SurrogateVault()
    result = deidentify("Call (617) 555-0142.", vault)
    assert vault.reveal(result.vault_id)  # non-empty mapping
    assert vault.reveal("does-not-exist") == {}


def test_no_phi_leaves_text_unchanged():
    text = "Patient reports fatigue and shortness of breath."
    result = deidentify(text)
    assert result.replacements == 0
    assert result.text == text
